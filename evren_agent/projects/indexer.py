"""Codebase indexing, symbol parsing, TODO extractor, and secret sanitizer."""
from __future__ import annotations

import ast
import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# Files and directories to always exclude from indexing and LLM context
IGNORED_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "dist", "build", ".venv", "venv",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".tox", ".idea", ".vscode",
    "target", "vendor", "bin", "obj", ".next", ".nuxt", "coverage",
}

IGNORED_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".pdf",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".mp3", ".wav", ".mp4", ".mov",
    ".ttf", ".woff", ".woff2", ".eot", ".db", ".sqlite", ".sqlite3",
}

# Secret detection patterns
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|auth|bearer)\s*[:=]\s*['\"][A-Za-z0-9_\-\.]{8,}['\"]"),
    re.compile(r"-----BEGIN (RSA|OPENSSH|DSA|EC|PGP)? PRIVATE KEY-----"),
    re.compile(r"(?i)ghp_[A-Za-z0-9]{36}"),
    re.compile(r"(?i)glpat-[A-Za-z0-9_\-]{20}"),
    re.compile(r"(?i)xox[baprs]-[A-Za-z0-9]{10,48}"),
]

SENSITIVE_FILENAMES = {
    ".env", ".env.local", ".env.production", ".env.development", ".env.staging",
    "id_rsa", "id_dsa", "id_ed25519", "credentials.json", "service-account.json",
    "secret.key", "secrets.yaml", "secrets.json",
}


def is_sensitive_file(file_path: str | Path) -> bool:
    """Checks if a file should NEVER be read or sent to an LLM."""
    p = Path(file_path)
    name = p.name.lower()
    if name in SENSITIVE_FILENAMES or name.startswith(".env"):
        return True
    if p.suffix.lower() in {".pem", ".key", ".p12", ".pfx", ".pkcs12"}:
        return True
    return False


def sanitize_secrets(text: str) -> str:
    """Masks secrets and sensitive credentials in content before context inclusion."""
    sanitized = text
    for pat in SECRET_PATTERNS:
        sanitized = pat.sub("[SECRET_FILTERED]", sanitized)
    return sanitized


class CodebaseIndexer:
    """Scans and indexes files, symbols, and TODOs from a project workspace."""

    def __init__(self, project_root: str | Path):
        self.root = Path(project_root)

    def scan_files(self, max_files: int = 1500) -> List[Path]:
        """Collects relevant source and text files in the project."""
        found: List[Path] = []
        if not self.root.exists():
            return found

        for root, dirs, files in os.walk(self.root):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            for f in files:
                p = Path(root) / f
                if p.suffix.lower() in IGNORED_EXTENSIONS or is_sensitive_file(p):
                    continue
                try:
                    # Skip files larger than 1MB
                    if p.stat().st_size > 1024 * 1024:
                        continue
                except OSError:
                    continue
                found.append(p)
                if len(found) >= max_files:
                    return found
        return found

    def index_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extracts symbols, classes, functions, imports, and TODOs from a single file."""
        try:
            rel_path = str(file_path.relative_to(self.root))
        except ValueError:
            rel_path = str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        ext = file_path.suffix.lower()

        classes: List[str] = []
        functions: List[str] = []
        imports: List[str] = []
        todos: List[Dict[str, Any]] = []

        # 1. Extract TODO / FIXME comments across any text file
        todo_regex = re.compile(r"(?i)\b(TODO|FIXME|HACK|XXX|BUG)\b:?\s*(.*)")
        for idx, line in enumerate(content.splitlines(), start=1):
            m = todo_regex.search(line)
            if m:
                tag = m.group(1).upper()
                msg = m.group(2).strip()
                todos.append({
                    "type": tag,
                    "line": idx,
                    "text": msg[:150],
                    "file": rel_path,
                })

        # 2. Extract AST symbols for Python
        if ext == ".py":
            try:
                tree = ast.parse(content, filename=rel_path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        classes.append(node.name)
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        functions.append(node.name)
                    elif isinstance(node, ast.Import):
                        for n in node.names:
                            imports.append(n.name)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.append(node.module)
            except SyntaxError:
                pass

        # 3. Regex fallback for JS/TS/Go/Rust/Java
        elif ext in {".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".cpp", ".cs"}:
            class_pat = re.compile(r"\bclass\s+([A-Za-z0-9_]+)")
            fn_pat = re.compile(r"\b(?:function|fn|func|def)\s+([A-Za-z0-9_]+)")
            import_pat = re.compile(r"(?:import|from)\s+['\"]([^'\"]+)['\"]")

            for m in class_pat.finditer(content):
                classes.append(m.group(1))
            for m in fn_pat.finditer(content):
                functions.append(m.group(1))
            for m in import_pat.finditer(content):
                imports.append(m.group(1))

        symbols = list(dict.fromkeys(classes + functions))

        return {
            "file_path": rel_path,
            "file_type": ext,
            "symbols": symbols,
            "classes": classes,
            "functions": functions,
            "imports": list(dict.fromkeys(imports)),
            "todos": todos,
            "file_hash": file_hash,
        }

    def search_codebase(
        self,
        query: str,
        indexed_data: List[Dict[str, Any]],
        limit: int = 15,
    ) -> List[Dict[str, Any]]:
        """Matches a search query across indexed symbols, paths, and content."""
        q_lower = query.lower().strip()
        tokens = [t for t in re.split(r"\W+", q_lower) if t]
        results = []

        for entry in indexed_data:
            path = entry["file_path"].lower()
            symbols = [s.lower() for s in entry.get("symbols", [])]
            imports = [i.lower() for i in entry.get("imports", [])]

            score = 0
            matched_symbols = []

            for token in tokens:
                if token in path:
                    score += 5
                for s in symbols:
                    if token in s:
                        score += 8
                        matched_symbols.append(s)
                for i in imports:
                    if token in i:
                        score += 3

            if score > 0:
                results.append({
                    "file_path": entry["file_path"],
                    "score": score,
                    "matched_symbols": list(set(matched_symbols))[:5],
                    "file_type": entry.get("file_type", ""),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
