"""Tests for forbidden import rule."""
from pathlib import Path

from drift.scanner.base import FileInfo, ImportEdge
from drift.rules.import_rule import check_forbidden_imports


def _make_file(rel_path: str, imports: list[tuple[str, str | None]]) -> FileInfo:
    return FileInfo(
        path=Path("/root") / rel_path,
        relative_path=rel_path,
        lines=10,
        imports=[
            ImportEdge(source_file=rel_path, target_module=mod, target_file=tgt, line=i + 1)
            for i, (mod, tgt) in enumerate(imports)
        ],
    )


class TestCheckForbiddenImports:
    def test_no_violations(self):
        files = [
            _make_file("src/api/routes.py", [("src.utils", "src/utils.py")]),
            _make_file("src/db/queries.py", []),
        ]
        results = check_forbidden_imports(files, ["src/api/**"], ["src/db/**"], "No DB in API")
        assert results == []

    def test_violation_detected(self):
        files = [
            _make_file("src/api/routes.py", [("src.db.queries", "src/db/queries.py")]),
        ]
        results = check_forbidden_imports(files, ["src/api/**"], ["src/db/**"], "No DB in API")
        assert len(results) == 1
        assert results[0]["file"] == "src/api/routes.py"
        assert results[0]["rule"] == "No DB in API"
        assert results[0]["type"] == "forbidden_import"

    def test_from_pattern_no_match(self):
        files = [
            _make_file("src/utils/helpers.py", [("src.db.queries", "src/db/queries.py")]),
        ]
        results = check_forbidden_imports(files, ["src/api/**"], ["src/db/**"], "No DB in API")
        assert results == []

    def test_multiple_violations(self):
        files = [
            _make_file("src/api/routes.py", [
                ("src.db.queries", "src/db/queries.py"),
                ("src.models.user", "src/models/user.py"),
            ]),
        ]
        results = check_forbidden_imports(
            files, ["src/api/**"], ["src/db/**", "src/models/**"], "Isolation"
        )
        assert len(results) == 2

    def test_violation_via_resolved_target(self):
        files = [
            _make_file("src/api/routes.py", [("something", "src/db/queries.py")]),
        ]
        results = check_forbidden_imports(files, ["src/api/**"], ["src/db/**"], "Rule")
        assert len(results) == 1
