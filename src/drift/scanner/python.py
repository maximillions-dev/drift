"""Python import scanner using AST."""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Sequence

from drift.scanner.base import BaseScanner, FileInfo, ImportEdge


class PythonScanner(BaseScanner):
    EXTENSIONS = {".py"}
    SKIP_DIRS = {
        "node_modules", "__pycache__", ".git", ".venv", "venv",
        ".env", "env", ".tox", "build", "dist", ".eggs", "*.egg-info",
    }
    SKIP_FILES = {"setup.py", "conftest.py"}

    def should_skip(self, path: Path) -> bool:
        if path.suffix not in self.EXTENSIONS:
            return True
        for part in path.parts:
            if part in self.SKIP_DIRS:
                return True
        if path.parent.name == "migrations":
            return True
        if path.name in self.SKIP_FILES:
            return True
        if path.name.startswith("test_") or path.name.endswith("_test.py"):
            return True
        return False

    def scan_file(self, path: Path, root: Path) -> FileInfo:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.count("\n") + 1

        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            return FileInfo(path=path, relative_path=str(path.relative_to(root)), lines=lines)

        imports: list[ImportEdge] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    resolved = self.resolve_import(alias.name, path, root)
                    imports.append(
                        ImportEdge(
                            source_file=str(path.relative_to(root)),
                            target_module=alias.name,
                            target_file=resolved,
                            line=node.lineno,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                resolved = self.resolve_import(node.module, path, root)
                if resolved:
                    imports.append(
                        ImportEdge(
                            source_file=str(path.relative_to(root)),
                            target_module=node.module,
                            target_file=resolved,
                            line=node.lineno,
                        )
                    )

        return FileInfo(
            path=path,
            relative_path=str(path.relative_to(root)),
            lines=lines,
            imports=imports,
        )

    def resolve_import(self, module: str, source_file: Path, root: Path) -> str | None:
        module_path = module.replace(".", "/")

        candidates: list[str] = [
            f"{module_path}.py",
            f"{module_path}/__init__.py",
        ]

        for candidate in candidates:
            full = (root / candidate).resolve()
            if full.exists():
                try:
                    return str(full.relative_to(root))
                except ValueError:
                    pass

        source_dir = source_file.parent
        for candidate in candidates:
            full = (source_dir / candidate).resolve()
            if full.exists():
                try:
                    return str(full.relative_to(root))
                except ValueError:
                    pass

        return None


def find_python_files(root: Path, skip_dirs: Sequence[str] | None = None) -> list[Path]:
    skip = set(skip_dirs or [])
    skip |= {"node_modules", "__pycache__", ".git", ".venv", "venv", ".env", "env",
             ".tox", "build", "dist", ".eggs", "*.egg-info", "migrations"}
    files = []
    for path in root.rglob("*.py"):
        if any(p in skip for p in path.parts):
            continue
        files.append(path)
    return sorted(files)
