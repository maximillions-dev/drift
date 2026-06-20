"""Base scanner abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ImportEdge:
    source_file: str
    target_module: str
    target_file: str | None
    line: int


@dataclass
class FileInfo:
    path: Path
    relative_path: str
    lines: int
    imports: list[ImportEdge] = field(default_factory=list)


class BaseScanner(ABC):
    """Language-specific scanner that extracts imports from files."""

    @abstractmethod
    def scan_file(self, path: Path, root: Path) -> FileInfo:
        ...

    def scan_directory(self, root: Path) -> list[FileInfo]:
        results: list[FileInfo] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if self.should_skip(path):
                continue
            results.append(self.scan_file(path, root))
        return results

    @abstractmethod
    def should_skip(self, path: Path) -> bool:
        ...

    @abstractmethod
    def resolve_import(self, module: str, source_file: Path, root: Path) -> str | None:
        ...
