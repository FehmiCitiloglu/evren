"""Git integration service for Evren Agent Projects."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class GitService:
    """Manages Git queries, commits, branches, and diff analysis for a project directory."""

    @staticmethod
    def is_git_repo(path: str | Path) -> bool:
        p = Path(path)
        return (p / ".git").exists()

    @staticmethod
    def _run_git(cwd: str | Path, args: List[str], timeout: float = 15.0) -> Tuple[int, str, str]:
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except Exception as e:
            return 1, "", str(e)

    @classmethod
    def get_current_branch(cls, path: str | Path) -> str:
        code, stdout, _ = cls._run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"])
        return stdout if code == 0 and stdout else "main"

    @classmethod
    def get_remote_url(cls, path: str | Path) -> str:
        code, stdout, _ = cls._run_git(path, ["config", "--get", "remote.origin.url"])
        return stdout if code == 0 else ""

    @classmethod
    def get_branches(cls, path: str | Path) -> List[str]:
        code, stdout, _ = cls._run_git(path, ["branch", "--format=%(refname:short)"])
        if code == 0 and stdout:
            return [b.strip() for b in stdout.splitlines() if b.strip()]
        return []

    @classmethod
    def get_status(cls, path: str | Path) -> Dict[str, Any]:
        """Returns structured status of modified, staged, and untracked files."""
        code, stdout, _ = cls._run_git(path, ["status", "--porcelain"])
        staged = []
        modified = []
        untracked = []

        if code == 0 and stdout:
            for line in stdout.splitlines():
                if len(line) < 3:
                    continue
                index_st = line[0]
                work_st = line[1]
                filepath = line[3:].strip()

                if index_st in ("M", "A", "D", "R", "C"):
                    staged.append({"path": filepath, "status": index_st})
                if work_st in ("M", "D"):
                    modified.append({"path": filepath, "status": work_st})
                elif index_st == "?" and work_st == "?":
                    untracked.append({"path": filepath, "status": "?"})

        ahead_behind = cls.get_ahead_behind(path)

        return {
            "branch": cls.get_current_branch(path),
            "staged": staged,
            "modified": modified,
            "untracked": untracked,
            "ahead": ahead_behind.get("ahead", 0),
            "behind": ahead_behind.get("behind", 0),
            "clean": len(staged) == 0 and len(modified) == 0 and len(untracked) == 0,
        }

    @classmethod
    def get_ahead_behind(cls, path: str | Path) -> Dict[str, int]:
        code, stdout, _ = cls._run_git(path, ["rev-list", "--left-right", "--count", "@{upstream}...HEAD"])
        if code == 0 and stdout:
            parts = stdout.split()
            if len(parts) == 2:
                try:
                    return {"behind": int(parts[0]), "ahead": int(parts[1])}
                except ValueError:
                    pass
        return {"ahead": 0, "behind": 0}

    @classmethod
    def get_recent_commits(cls, path: str | Path, limit: int = 15) -> List[Dict[str, Any]]:
        fmt = "%H%x1f%s%x1f%an%x1f%ad%x1f%h"
        code, stdout, _ = cls._run_git(path, ["log", f"-{limit}", f"--pretty=format:{fmt}", "--date=relative"])
        commits = []
        if code == 0 and stdout:
            for line in stdout.splitlines():
                parts = line.split("\x1f")
                if len(parts) >= 5:
                    commits.append({
                        "hash": parts[0],
                        "short_hash": parts[4],
                        "message": parts[1],
                        "author": parts[2],
                        "relative_date": parts[3],
                    })
        return commits

    @classmethod
    def get_diff(cls, path: str | Path, staged: bool = False, max_lines: int = 500) -> str:
        args = ["diff", "--cached"] if staged else ["diff"]
        code, stdout, _ = cls._run_git(path, args)
        if code == 0 and stdout:
            lines = stdout.splitlines()
            if len(lines) > max_lines:
                return "\n".join(lines[:max_lines]) + f"\n... (Diff truncated at {max_lines} lines)"
            return stdout
        return ""

    @classmethod
    def get_commit_diff(cls, path: str | Path, commit_hash: str) -> str:
        code, stdout, _ = cls._run_git(path, ["show", commit_hash, "--stat"])
        return stdout if code == 0 else ""

    @classmethod
    def find_tasks_in_commits(cls, commits: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Maps detected task keys (e.g. TASK-123 or #123) to commit hashes."""
        mapping: Dict[str, List[str]] = {}
        pattern = re.compile(r"(?:TASK|EVREN)[-_](\d+)|#(\d+)", re.IGNORECASE)
        for c in commits:
            msg = c.get("message", "")
            matches = pattern.findall(msg)
            for m in matches:
                key = m[0] or m[1]
                if key:
                    t_key = f"TASK-{key}"
                    mapping.setdefault(t_key, []).append(c["short_hash"])
        return mapping

    @classmethod
    def clone_repository(cls, repo_url: str, target_dir: str | Path) -> Tuple[bool, str]:
        target = Path(target_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            res = subprocess.run(
                ["git", "clone", repo_url, str(target)],
                capture_output=True,
                text=True,
                timeout=120.0,
            )
            if res.returncode == 0:
                return True, f"Repository cloned successfully to {target}"
            return False, res.stderr or "Git clone failed"
        except Exception as e:
            return False, str(e)
