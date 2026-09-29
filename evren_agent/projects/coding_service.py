"""Coding agent orchestration, session recording, Ask Project, and Universal Search."""
from __future__ import annotations

import datetime
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import uuid

from evren_agent.projects.context_builder import ProjectContextBuilder
from evren_agent.projects.db import ProjectDatabase
from evren_agent.projects.git_service import GitService
from evren_agent.projects.indexer import CodebaseIndexer, is_sensitive_file
from evren_agent.projects.models import (
    CodingSession,
    Feature,
    Project,
    Task,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class ProjectCodingService:
    """Orchestrates coding sessions, task planning, project Q&A, and universal search."""

    def __init__(self, db: ProjectDatabase):
        self.db = db

    def prepare_task_agent_prompt(
        self,
        project_id: str,
        task_id: str,
    ) -> Dict[str, Any]:
        """Builds structured context and prompt for 'Start with Agent' (Section 34)."""
        project = self.db.get_project(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found.")

        task = self.db.get_task(task_id)
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")

        feature = self.db.get_feature(task.feature_id) if task.feature_id else None
        settings = self.db.get_settings(project_id)
        instructions = self.db.list_instructions(project_id)
        memories = self.db.list_memories(project_id, status="approved")
        adrs = self.db.list_adrs(project_id)
        sessions = self.db.list_sessions(project_id)
        last_session = sessions[0] if sessions else None

        git_diff = GitService.get_diff(project.local_path, staged=False, max_lines=150)

        # Read relevant files if specified in task
        relevant_files: Dict[str, str] = {}
        for rf in task.related_files:
            fp = Path(project.local_path) / rf
            if fp.exists() and fp.is_file() and not is_sensitive_file(fp):
                try:
                    relevant_files[rf] = fp.read_text(encoding="utf-8", errors="ignore")[:3000]
                except Exception:
                    pass

        builder = ProjectContextBuilder(
            project=project,
            settings=settings,
            instructions=instructions,
            memories=memories,
            current_feature=feature,
            current_task=task,
            adrs=adrs,
            relevant_files=relevant_files,
            git_diff=git_diff,
            last_session=last_session,
            total_token_budget=6000,
        )

        base_role = (
            "You are the Evren Coding Agent working inside this software project workspace.\n"
            "Follow the lifecycle: 1. Understand requirement, 2. Plan solution, 3. Implement code, "
            "4. Verify with tests, 5. Summarize state update.\n"
            "Do not make destructive changes outside the task scope."
        )

        system_prompt = builder.assemble_system_prompt(base_role)
        visibility_report = builder.get_visibility_report()

        initial_user_message = (
            f"Please implement task '{task.title}'.\n\n"
            f"Task Description:\n{task.description or 'No description provided.'}\n\n"
        )
        if task.acceptance_criteria:
            initial_user_message += "Acceptance Criteria:\n" + "\n".join(f"- {c}" for c in task.acceptance_criteria) + "\n\n"
        initial_user_message += "First, outline your step-by-step implementation plan."

        return {
            "project": project,
            "task": task,
            "feature": feature,
            "system_prompt": system_prompt,
            "user_prompt": initial_user_message,
            "visibility_report": visibility_report,
            "model": settings.coding_model,
        }

    def record_session(
        self,
        project_id: str,
        title: str,
        user_request: str,
        plan: str,
        agent_actions: List[Dict[str, Any]],
        files_changed: List[str],
        commands_executed: List[str],
        tests_executed: List[Dict[str, Any]],
        git_diff: str,
        result: str,
        summary: str,
        duration_sec: int = 0,
        task_id: Optional[str] = None,
        feature_id: Optional[str] = None,
        tokens_used: int = 0,
        cost_est: float = 0.0,
    ) -> CodingSession:
        """Saves a coding session record (Section 31)."""
        project = self.db.get_project(project_id)
        commit_hash = ""
        if project:
            commits = GitService.get_recent_commits(project.local_path, limit=1)
            commit_hash = commits[0]["short_hash"] if commits else ""

        session = CodingSession(
            id=f"sess_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            task_id=task_id,
            feature_id=feature_id,
            title=title,
            user_request=user_request,
            plan=plan,
            agent_actions=agent_actions,
            files_changed=files_changed,
            commands_executed=commands_executed,
            tests_executed=tests_executed,
            git_diff=git_diff,
            result=result,
            summary=summary,
            duration_sec=duration_sec,
            commit_hash=commit_hash,
            tokens_used=tokens_used,
            cost_est=cost_est,
        )
        self.db.save_session(session)
        return session

    def ask_project(
        self,
        project_id: str,
        question: str,
    ) -> Dict[str, Any]:
        """Provides an authoritative answer citing code, tasks, ADRs, and commits (Section 45)."""
        project = self.db.get_project(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found.")

        # Search across symbols and paths
        indexer = CodebaseIndexer(project.local_path)
        all_indexed = self.db.get_all_code_indexes(project_id)
        search_matches = indexer.search_codebase(question, all_indexed, limit=6)

        tasks = self.db.list_tasks(project_id)
        matched_tasks = [t for t in tasks if any(w in (t.title + t.description).lower() for w in question.lower().split() if len(w) > 3)][:4]

        adrs = self.db.list_adrs(project_id)
        matched_adrs = [a for a in adrs if any(w in (a.title + a.context + a.decision).lower() for w in question.lower().split() if len(w) > 3)][:2]

        commits = GitService.get_recent_commits(project.local_path, limit=8)

        # Build citations
        citations = []
        for m in search_matches:
            citations.append({"type": "file", "ref": m["file_path"], "detail": f"Matched symbols: {', '.join(m.get('matched_symbols', []))}"})
        for t in matched_tasks:
            citations.append({"type": "task", "ref": f"TASK-{t.id[:6]}", "detail": t.title})
        for a in matched_adrs:
            citations.append({"type": "adr", "ref": f"ADR-{a.adr_number}", "detail": a.title})

        context_prompt = (
            f"You are the Project Knowledge Assistant for '{project.name}'.\n"
            f"Question: {question}\n\n"
            "Relevant Code Files:\n" + "\n".join(f"- {c['ref']} ({c['detail']})" for c in citations if c['type'] == 'file') + "\n\n"
            "Relevant Tasks:\n" + "\n".join(f"- {c['ref']}: {c['detail']}" for c in citations if c['type'] == 'task') + "\n\n"
            "Relevant Architecture Decisions:\n" + "\n".join(f"- {c['ref']}: {c['detail']}" for c in citations if c['type'] == 'adr') + "\n\n"
            "Answer the question thoroughly, citing the specific files and tasks above."
        )

        return {
            "question": question,
            "citations": citations,
            "context_prompt": context_prompt,
            "matched_files": [m["file_path"] for m in search_matches],
            "matched_tasks": matched_tasks,
        }

    def universal_search(
        self,
        project_id: str,
        query: str,
        limit_per_category: int = 5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Universal search across code, tasks, features, bugs, docs, memory, and commits (Section 44)."""
        project = self.db.get_project(project_id)
        if not project:
            return {}

        q = query.lower().strip()
        tokens = [t for t in q.split() if len(t) > 2]
        if not tokens:
            return {}

        results: Dict[str, List[Dict[str, Any]]] = {
            "code": [],
            "tasks": [],
            "features": [],
            "bugs": [],
            "docs": [],
            "memories": [],
            "adrs": [],
            "commits": [],
        }

        # 1. Code symbols
        indexer = CodebaseIndexer(project.local_path)
        all_indexed = self.db.get_all_code_indexes(project_id)
        code_matches = indexer.search_codebase(query, all_indexed, limit=limit_per_category)
        for cm in code_matches:
            results["code"].append({
                "title": cm["file_path"],
                "subtitle": f"Symbols: {', '.join(cm.get('matched_symbols', []))}",
                "ref": cm["file_path"],
            })

        # 2. Tasks
        for t in self.db.list_tasks(project_id):
            if any(tok in (t.title + t.description).lower() for tok in tokens):
                results["tasks"].append({
                    "title": t.title,
                    "subtitle": f"[{t.status}] Priority: {t.priority}, Type: {t.task_type}",
                    "ref": t.id,
                })
                if len(results["tasks"]) >= limit_per_category:
                    break

        # 3. Features
        for f in self.db.list_features(project_id):
            if any(tok in (f.title + f.description).lower() for tok in tokens):
                results["features"].append({
                    "title": f.title,
                    "subtitle": f"Status: {f.status}, Priority: {f.priority}",
                    "ref": f.id,
                })
                if len(results["features"]) >= limit_per_category:
                    break

        # 4. Bugs
        for b in self.db.list_bugs(project_id):
            if any(tok in (b.title + b.description).lower() for tok in tokens):
                results["bugs"].append({
                    "title": b.title,
                    "subtitle": f"Severity: {b.severity}, Status: {b.status}",
                    "ref": b.id,
                })
                if len(results["bugs"]) >= limit_per_category:
                    break

        # 5. Docs
        for d in self.db.list_documents(project_id):
            if any(tok in (d.title + d.content).lower() for tok in tokens):
                results["docs"].append({
                    "title": d.title,
                    "subtitle": f"Type: {d.doc_type}",
                    "ref": d.id,
                })
                if len(results["docs"]) >= limit_per_category:
                    break

        # 6. Memories
        for m in self.db.list_memories(project_id):
            if any(tok in m.content.lower() for tok in tokens):
                results["memories"].append({
                    "title": m.content[:60],
                    "subtitle": f"Type: {m.memory_type} ({m.status})",
                    "ref": m.id,
                })
                if len(results["memories"]) >= limit_per_category:
                    break

        # 7. ADRs
        for a in self.db.list_adrs(project_id):
            if any(tok in (a.title + a.decision + a.context).lower() for tok in tokens):
                results["adrs"].append({
                    "title": f"ADR {a.adr_number}: {a.title}",
                    "subtitle": a.decision[:80],
                    "ref": a.id,
                })
                if len(results["adrs"]) >= limit_per_category:
                    break

        # 8. Commits
        for c in GitService.get_recent_commits(project.local_path, limit=25):
            if any(tok in c["message"].lower() for tok in tokens):
                results["commits"].append({
                    "title": c["message"],
                    "subtitle": f"Hash: {c['short_hash']} by {c['author']} ({c['relative_date']})",
                    "ref": c["hash"],
                })
                if len(results["commits"]) >= limit_per_category:
                    break

        return results
