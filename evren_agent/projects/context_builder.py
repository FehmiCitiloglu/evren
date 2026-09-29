"""Dynamic project context builder with token budgeting and security sanitization."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from evren_agent.projects.indexer import is_sensitive_file, sanitize_secrets
from evren_agent.projects.models import (
    ArchitectureDecision,
    CodingSession,
    Document,
    Feature,
    Project,
    ProjectInstruction,
    ProjectMemory,
    ProjectSettings,
    Task,
)


def approx_tokens(text: str) -> int:
    """Rough estimation: ~4 chars per token for typical code and English/Turkish text."""
    return max(1, len(text) // 4)


class ContextSlice:
    def __init__(self, name: str, content: str, budget_tokens: int):
        self.name = name
        self.raw_content = content
        self.budget_tokens = budget_tokens
        self.char_budget = budget_tokens * 4
        self.sanitized_content = sanitize_secrets(content)

    def get_truncated_text(self) -> str:
        if len(self.sanitized_content) <= self.char_budget:
            return self.sanitized_content
        return self.sanitized_content[:self.char_budget] + f"\n... [Truncated to fit {self.budget_tokens} token budget]"

    def token_count(self) -> int:
        return approx_tokens(self.get_truncated_text())


class ProjectContextBuilder:
    """Assembles prompt context respecting token budgets and secret sanitization."""

    def __init__(
        self,
        project: Project,
        settings: ProjectSettings,
        instructions: List[ProjectInstruction],
        memories: List[ProjectMemory],
        current_feature: Optional[Feature] = None,
        current_task: Optional[Task] = None,
        adrs: Optional[List[ArchitectureDecision]] = None,
        relevant_files: Optional[Dict[str, str]] = None,
        git_diff: Optional[str] = None,
        last_session: Optional[CodingSession] = None,
        total_token_budget: int = 8000,
    ):
        self.project = project
        self.settings = settings
        self.instructions = [i for i in instructions if i.is_active]
        self.memories = [m for m in memories if m.status in ("approved", "pinned")]
        self.current_feature = current_feature
        self.current_task = current_task
        self.adrs = adrs or []
        self.relevant_files = relevant_files or {}
        self.git_diff = git_diff or ""
        self.last_session = last_session
        self.total_budget = total_token_budget

    def build_slices(self) -> Dict[str, ContextSlice]:
        ratios = self.settings.token_budget or {
            "instructions": 5,
            "feature_context": 10,
            "memory": 10,
            "code": 50,
            "git": 10,
            "session": 15,
        }

        # 1. Instructions
        inst_text = ""
        for inst in sorted(self.instructions, key=lambda x: x.priority):
            inst_text += f"- [{inst.category} / {inst.scope}] {inst.title}:\n  {inst.content}\n"
        b_inst = (self.total_budget * ratios.get("instructions", 5)) // 100
        slice_inst = ContextSlice("Instructions", inst_text.strip(), max(100, b_inst))

        # 2. Memories & ADRs
        mem_text = ""
        for mem in self.memories:
            pin_badge = "[PINNED] " if mem.status == "pinned" else ""
            mem_text += f"- {pin_badge}({mem.memory_type}): {mem.content}\n"
        for adr in self.adrs[:4]:
            mem_text += f"- ADR {adr.adr_number} ({adr.title}): {adr.decision}\n"
        b_mem = (self.total_budget * ratios.get("memory", 10)) // 100
        slice_mem = ContextSlice("Memory & Decisions", mem_text.strip(), max(100, b_mem))

        # 3. Feature & Task
        feat_text = ""
        if self.current_feature:
            feat_text += f"FEATURE: {self.current_feature.title} (Status: {self.current_feature.status})\n"
            feat_text += f"Description: {self.current_feature.description}\n"
            if self.current_feature.requirements:
                feat_text += "Requirements:\n" + "\n".join(f"  * {r}" for r in self.current_feature.requirements) + "\n"
            if self.current_feature.acceptance_criteria:
                feat_text += "Acceptance Criteria:\n" + "\n".join(f"  * {c}" for r in self.current_feature.acceptance_criteria for c in [r]) + "\n"

        if self.current_task:
            feat_text += f"\nCURRENT TASK: {self.current_task.title} [{self.current_task.task_type} / {self.current_task.priority}]\n"
            feat_text += f"Description: {self.current_task.description}\n"
            if self.current_task.acceptance_criteria:
                feat_text += "Task Criteria:\n" + "\n".join(f"  * {c}" for c in self.current_task.acceptance_criteria) + "\n"

        b_feat = (self.total_budget * ratios.get("feature_context", 10)) // 100
        slice_feat = ContextSlice("Feature & Task", feat_text.strip(), max(100, b_feat))

        # 4. Relevant Code Files
        code_text = ""
        for file_path, content in self.relevant_files.items():
            if is_sensitive_file(file_path):
                continue
            code_text += f"\n--- FILE: {file_path} ---\n{content}\n"
        b_code = (self.total_budget * ratios.get("code", 50)) // 100
        slice_code = ContextSlice("Relevant Code", code_text.strip(), max(200, b_code))

        # 5. Git Diff
        b_git = (self.total_budget * ratios.get("git", 10)) // 100
        slice_git = ContextSlice("Git Diff", self.git_diff.strip(), max(100, b_git))

        # 6. Session Summary
        session_text = ""
        if self.last_session:
            session_text += f"Previous Session ({self.last_session.title}):\n"
            session_text += f"Summary: {self.last_session.summary}\n"
            if self.last_session.files_changed:
                session_text += "Files touched: " + ", ".join(self.last_session.files_changed) + "\n"
        b_sess = (self.total_budget * ratios.get("session", 15)) // 100
        slice_sess = ContextSlice("Session History", session_text.strip(), max(100, b_sess))

        return {
            "instructions": slice_inst,
            "memory": slice_mem,
            "feature": slice_feat,
            "code": slice_code,
            "git": slice_git,
            "session": slice_sess,
        }

    def assemble_system_prompt(self, base_role_prompt: str) -> str:
        slices = self.build_slices()
        parts = [base_role_prompt]

        header = f"\n=== PROJECT: {self.project.name} ==="
        if self.project.description:
            header += f"\nDescription: {self.project.description}"
        if self.project.tech_stack:
            tech_desc = ", ".join(f"{k}: {', '.join(v)}" for k, v in self.project.tech_stack.items())
            header += f"\nTech Stack: {tech_desc}"
        parts.append(header)

        for key in ["instructions", "memory", "feature", "code", "git", "session"]:
            sl = slices[key]
            text = sl.get_truncated_text()
            if text:
                parts.append(f"\n=== {sl.name.upper()} ===\n{text}")

        return "\n".join(parts)

    def get_visibility_report(self) -> List[Dict[str, Any]]:
        """Provides transparency on tokens, characters, and items included in LLM context."""
        slices = self.build_slices()
        report = []
        for key, sl in slices.items():
            report.append({
                "key": key,
                "name": sl.name,
                "token_budget": sl.budget_tokens,
                "tokens_used": sl.token_count(),
                "has_content": bool(sl.raw_content.strip()),
                "sample": sl.get_truncated_text()[:180],
            })
        return report
