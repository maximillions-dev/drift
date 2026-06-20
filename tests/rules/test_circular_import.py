"""Tests for circular import detection."""
from pathlib import Path

from drift.scanner.base import FileInfo, ImportEdge
from drift.rules.circular_import import find_circular_imports


def _make_file(rel_path: str, deps: list[str]) -> FileInfo:
    return FileInfo(
        path=Path("/root") / rel_path,
        relative_path=rel_path,
        lines=10,
        imports=[
            ImportEdge(source_file=rel_path, target_module="", target_file=tgt, line=i + 1)
            for i, tgt in enumerate(deps)
        ],
    )


class TestFindCircularImports:
    def test_no_cycles(self):
        files = [
            _make_file("a.py", ["b.py"]),
            _make_file("b.py", ["c.py"]),
            _make_file("c.py", []),
        ]
        results = find_circular_imports(files, ["**/*.py"], "No cycles")
        assert results == []

    def test_simple_cycle(self):
        files = [
            _make_file("a.py", ["b.py"]),
            _make_file("b.py", ["a.py"]),
        ]
        results = find_circular_imports(files, ["**/*.py"], "No cycles")
        assert len(results) == 1
        assert results[0]["rule"] == "No cycles"
        assert results[0]["type"] == "circular_import"
        assert "a.py" in results[0]["message"]
        assert "b.py" in results[0]["message"]

    def test_self_import_is_cycle(self):
        files = [
            _make_file("a.py", ["a.py"]),
        ]
        results = find_circular_imports(files, ["**/*.py"], "No self-import")
        assert len(results) == 1

    def test_cycle_outside_path_pattern(self):
        """Files not matching the path patterns should be ignored."""
        files = [
            _make_file("src/lib/a.py", ["b.py"]),
            _make_file("src/lib/b.py", ["a.py"]),
        ]
        results = find_circular_imports(files, ["src/other/**"], "No cycles")
        assert results == []

    def test_larger_cycle(self):
        files = [
            _make_file("a.py", ["b.py"]),
            _make_file("b.py", ["c.py"]),
            _make_file("c.py", ["d.py"]),
            _make_file("d.py", ["a.py"]),
        ]
        results = find_circular_imports(files, ["**/*.py"], "No cycles")
        assert len(results) == 1
        assert len(results[0]["cycle"]) == 5  # includes duplicated start node

    def test_dedup_identical_cycles(self):
        """a→b, b→a should produce exactly one violation."""
        files = [
            _make_file("a.py", ["b.py"]),
            _make_file("b.py", ["a.py"]),
            _make_file("c.py", ["a.py"]),
        ]
        results = find_circular_imports(files, ["**/*.py"], "No cycles")
        assert len(results) == 1
