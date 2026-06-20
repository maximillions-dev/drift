"""Forbidden import rule — the killer feature."""
from __future__ import annotations

from drift.config import glob_match
from drift.scanner.base import FileInfo


def check_forbidden_imports(
    files: list[FileInfo],
    from_patterns: list[str],
    forbid_patterns: list[str],
    rule_name: str,
) -> list[dict]:
    violations: list[dict] = []

    for f in files:
        matches_from = any(glob_match(p, f.relative_path) for p in from_patterns)
        if not matches_from:
            continue

        for imp in f.imports:
            targets = []
            if imp.target_file:
                targets.append(imp.target_file)
            targets.append(imp.target_module)

            for forbid_pat in forbid_patterns:
                for target in targets:
                    if glob_match(forbid_pat, target):
                        violations.append(
                            {
                                "rule": rule_name,
                                "type": "forbidden_import",
                                "file": f.relative_path,
                                "line": imp.line,
                                "message": (
                                    f"imports '{imp.target_module}' "
                                    f"({forbid_pat})"
                                ),
                                "target": imp.target_module,
                                "forbid_pattern": forbid_pat,
                            }
                        )
                        break
                else:
                    continue
                break

    return violations
