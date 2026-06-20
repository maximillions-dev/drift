"""Tests for Python scanner."""
from pathlib import Path
import tempfile

from drift.scanner.python import PythonScanner


class TestPythonScannerScanFile:
    def test_simple_import(self):
        scanner = PythonScanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            (src / "main.py").write_text("import os\nimport sys\n")
            info = scanner.scan_file(src / "main.py", root)
            assert info.relative_path == "src/main.py"
            assert info.lines == 3  # trailing newline adds a line
            assert len(info.imports) >= 2

    def test_from_import(self):
        scanner = PythonScanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create a resolvable local module
            (root / "mylib.py").write_text("")
            (root / "main.py").write_text("from mylib import something\n")
            info = scanner.scan_file(root / "main.py", root)
            assert len(info.imports) == 1
            assert info.imports[0].target_module == "mylib"

    def test_syntax_error_returns_empty(self):
        scanner = PythonScanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "broken.py").write_text("this is not valid python {{{")
            info = scanner.scan_file(root / "broken.py", root)
            assert info.imports == []

    def test_resolve_import(self):
        scanner = PythonScanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mymod.py").write_text("")
            resolved = scanner.resolve_import("mymod", root / "main.py", root)
            assert resolved == "mymod.py"

    def test_resolve_package(self):
        scanner = PythonScanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "mypkg"
            pkg.mkdir()
            (pkg / "__init__.py").write_text("")
            resolved = scanner.resolve_import("mypkg", root / "main.py", root)
            assert resolved == "mypkg/__init__.py"


class TestPythonScannerScanDirectory:
    def test_finds_py_files(self):
        scanner = PythonScanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("")
            (root / "b.py").write_text("")
            files = scanner.scan_directory(root)
            assert len(files) == 2

    def test_skips_test_files(self):
        scanner = PythonScanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("")
            (root / "test_main.py").write_text("")
            (root / "main_test.py").write_text("")
            files = scanner.scan_directory(root)
            assert len(files) == 1
            assert files[0].relative_path == "main.py"

    def test_skips_pycache(self):
        scanner = PythonScanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("")
            cache = root / "__pycache__"
            cache.mkdir()
            (cache / "cached.py").write_text("")
            files = scanner.scan_directory(root)
            assert len(files) == 1
