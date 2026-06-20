"""Config parsing for .drift.yaml rules."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml


@dataclass
class RuleConfig:
    type: Literal["forbid_import", "no_circular", "max_lines", "max_files"]
    rule: str = ""
    path: str = ""
    from_path: str = ""
    forbid: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)
    limit: int = 0

    def __post_init__(self):
        if self.type == "forbid_import":
            if self.from_path and not self.paths:
                self.paths = [self.from_path]
            if not self.from_path and self.paths:
                self.from_path = self.paths[0]

    @classmethod
    def from_dict(cls, d: dict) -> "RuleConfig":
        return cls(
            type=d.get("type", ""),
            rule=d.get("rule", ""),
            path=d.get("path", d.get("paths", [""])[0] if d.get("paths") else ""),
            from_path=d.get("from", ""),
            forbid=d.get("forbid", []),
            paths=d.get("paths", [d.get("path", "")] if d.get("path") else []),
            limit=d.get("limit", 0),
        )


@dataclass
class DriftConfig:
    rules: list[RuleConfig] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path | str) -> "DriftConfig":
        path = Path(path)
        if not path.exists():
            return cls()
        raw = yaml.safe_load(path.read_text())
        if not raw or not isinstance(raw, dict):
            return cls()
        rules_raw = raw.get("rules")
        if not rules_raw or not isinstance(rules_raw, list):
            return cls()
        return cls(rules=[RuleConfig.from_dict(r) for r in rules_raw])


def glob_match(pattern: str, filepath: str) -> bool:
    """Match a glob-like pattern against a filepath.
    Supports ** (recursive), * (wildcard), and ? (single char).
    """
    parts = pattern.split("/")
    fparts = filepath.split("/")

    i, j = 0, 0
    while i < len(parts) and j < len(fparts):
        if parts[i] == "**":
            if i + 1 >= len(parts):
                return True
            rest = "/".join(parts[i + 1 :])
            for k in range(j, len(fparts)):
                if glob_match(rest, "/".join(fparts[k:])):
                    return True
            return False
        if not _match_segment(parts[i], fparts[j]):
            return False
        i += 1
        j += 1
    return i == len(parts) and j == len(fparts)


def _match_segment(pattern: str, segment: str) -> bool:
    regex = "^" + re.escape(pattern).replace("\\*", ".*").replace("\\?", ".") + "$"
    return bool(re.match(regex, segment))
