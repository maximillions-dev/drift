"""Tests for file size and count limits."""
from pathlib import Path
import tempfile

from drift.scanner.base import FileInfo
from drift.rules.file_limits import check_max_lines, check_max_files


class TestCheckMaxLines:
    def test_under_limit(self):
        files = [FileInfo(path=Path("a.py"), relative_path="src/a.py", lines=50)]
        results = check_max_lines(files, "src/**", 100, "Keep files short")
        assert results == []

    def test_over_limit(self):
        files = [FileInfo(path=Path("a.py"), relative_path="src/a.py", lines=200)]
        results = check_max_lines(files, "src/**", 100, "Keep files short")
        assert len(results) == 1
        assert results[0]["file"] == "src/a.py"
        assert results[0]["actual"] == 200
        assert results[0]["limit"] == 100

    def test_outside_pattern(self):
        files = [FileInfo(path=Path("a.py"), relative_path="tests/a.py", lines=999)]
        results = check_max_lines(files, "src/**", 100, "Keep files short")
        assert results == []

    def test_multiple_over_limit(self):
        files = [
            FileInfo(path=Path("a.py"), relative_path="src/a.py", lines=200),
            FileInfo(path=Path("b.py"), relative_path="src/b.py", lines=300),
        ]
        results = check_max_lines(files, "src/**", 250, "Keep files short")
        assert len(results) == 1
        assert results[0]["file"] == "src/b.py"


class TestCheckMaxFiles:
    def test_under_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "a.py").write_text("")
            (root / "src" / "b.py").write_text("")
            results = check_max_files(root, "src/**", 10, "Not too many")
            assert results == []

    def test_over_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "utils"
            d.mkdir()
            for i in range(5):
                (d / f"file{i}.py").write_text("")
            results = check_max_files(root, "utils/**", 3, "Limit utils")
            assert len(results) == 1
            assert results[0]["actual"] == 5
            assert results[0]["limit"] == 3
