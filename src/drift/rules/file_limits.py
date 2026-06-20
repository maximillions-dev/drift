"""File size and count limit rules."""
from __future__ import annotations

from pathlib import Path

from drift.config import glob_match
from drift.scanner.base import FileInfo


def check_max_lines(
    files: list[FileInfo],
    path_pattern: str,
    limit: int,
    rule_name: str,
) -> list[dict]:
    violations = []
    for f in files:
        if not glob_match(path_pattern, f.relative_path):
            continue
        if f.lines > limit:
            violations.append({
                "rule": rule_name,
                "type": "max_lines",
                "file": f.relative_path,
                "line": 1,
                "message": f"{f.lines} lines (limit: {limit})",
                "actual": f.lines,
                "limit": limit,
            })
    return violations


def check_max_files(
    root: Path,
    path_pattern: str,
    limit: int,
    rule_name: str,
) -> list[dict]:
    matching = [p for p in root.rglob("*") if p.is_file() and glob_match(path_pattern, str(p.relative_to(root)))]
    count = len(matching)
    violations = []
    if count > limit:
        violations.append({
            "rule": rule_name,
            "type": "max_files",
            "file": path_pattern,
            "line": 1,
            "message": f"{count} files (limit: {limit})",
            "actual": count,
            "limit": limit,
        })
    return violations
