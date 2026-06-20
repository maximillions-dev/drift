"""JavaScript/TypeScript import scanner using regex."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

from drift.scanner.base import BaseScanner, FileInfo, ImportEdge


class JavascriptScanner(BaseScanner):
    EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
    SKIP_DIRS = {
        "node_modules", ".git", ".venv", "venv", ".next", "dist",
        "build", ".cache", "coverage", ".nyc_output",
    }

    IMPORT_ES_RE = re.compile(
        r'(?:import|export)\s+(?:(?:\{[^}]*\})\s*(?:from\s+)?|(?:\*\s+as\s+\w+\s+from\s+)|(?:\w+\s+(?:,\s*\{[^}]*\})?\s+from\s+))?[\'"](\.[^\'"]+|[^\'"]*)[\'"]'
    )
    REQUIRE_RE = re.compile(r'(?:const|let|var)\s+\w+\s*=\s*require\([\'"]([^\'"]+)[\'"]\)')
    DYNAMIC_IMPORT_RE = re.compile(r'import\([\'"]([^\'"]+)[\'"]\)')
    RE_EXPORT_RE = re.compile(r'export\s+(?:\{[^}]*\}|[\w*]+)\s+from\s+[\'"]([^\'"]+)[\'"]')

    def should_skip(self, path: Path) -> bool:
        if path.suffix not in self.EXTENSIONS:
            return True
        for part in path.parts:
            if part in self.SKIP_DIRS:
                return True
        if "node_modules" in path.parts:
            return True
        return False

    def scan_file(self, path: Path, root: Path) -> FileInfo:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.count("\n") + 1
        imports: list[ImportEdge] = []
        rel_path = str(path.relative_to(root))

        for regex in [self.IMPORT_ES_RE, self.REQUIRE_RE, self.DYNAMIC_IMPORT_RE,
                       self.RE_EXPORT_RE]:
            for m in regex.finditer(text):
                spec = m.group(1)
                line_no = text[: m.start()].count("\n") + 1
                resolved = self.resolve_import(spec, path, root)
                imports.append(
                    ImportEdge(
                        source_file=rel_path,
                        target_module=spec,
                        target_file=resolved,
                        line=line_no,
                    )
                )

        return FileInfo(
            path=path,
            relative_path=rel_path,
            lines=lines,
            imports=imports,
        )

    JS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts"}

    def resolve_import(self, spec: str, source_file: Path, root: Path) -> str | None:
        if not spec.startswith((".", "/")):
            return None

        source_dir = source_file.parent
        candidates: list[str] = [spec]

        for ext in self.JS_EXTENSIONS:
            candidates.append(f"{spec}{ext}")
        for ext in self.JS_EXTENSIONS:
            candidates.append(f"{spec}/index{ext}")

        for candidate in candidates:
            full = (source_dir / candidate).resolve()
            if full.exists() and full.is_file():
                try:
                    return str(full.relative_to(root))
                except ValueError:
                    pass
        return None


def find_js_files(root: Path, skip_dirs: Sequence[str] | None = None) -> list[Path]:
    skip = set(skip_dirs or [])
    skip |= {"node_modules", ".git", ".next", "dist", "build", ".cache", "coverage"}
    exts = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
    files = []
    for path in root.rglob("*"):
        if path.suffix not in exts:
            continue
        if any(p in skip for p in path.parts):
            continue
        files.append(path)
    return sorted(files)
