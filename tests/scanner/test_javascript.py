"""Tests for JavaScript/TypeScript scanner."""
from pathlib import Path
import tempfile

from drift.scanner.javascript import JavascriptScanner


class TestJavascriptScannerScanFile:
    def test_es_import(self):
        scanner = JavascriptScanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.ts").write_text('import { foo } from "./helper";\n')
            info = scanner.scan_file(root / "index.ts", root)
            assert len(info.imports) == 1
            assert info.imports[0].target_module == "./helper"

    def test_require(self):
        scanner = JavascriptScanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.js").write_text('const fs = require("fs");\n')
            info = scanner.scan_file(root / "app.js", root)
            assert len(info.imports) == 1
            assert "fs" in info.imports[0].target_module

    def test_dynamic_import(self):
        scanner = JavascriptScanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "page.js").write_text('const mod = await import("./lazy.js");\n')
            info = scanner.scan_file(root / "page.js", root)
            assert len(info.imports) == 1
            assert info.imports[0].target_module == "./lazy.js"

    def test_line_counting(self):
        scanner = JavascriptScanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.js").write_text("// line 1\nimport { x } from './a';\n// line 3\n")
            info = scanner.scan_file(root / "main.js", root)
            assert info.lines >= 3


class TestJavascriptScannerScanDirectory:
    def test_finds_js_ts_files(self):
        scanner = JavascriptScanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.js").write_text("")
            (root / "b.ts").write_text("")
            (root / "c.tsx").write_text("")
            (root / "readme.md").write_text("")
            files = scanner.scan_directory(root)
            assert len(files) == 3

    def test_skips_node_modules(self):
        scanner = JavascriptScanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.js").write_text("")
            nm = root / "node_modules"
            nm.mkdir()
            (nm / "lodash.js").write_text("")
            files = scanner.scan_directory(root)
            assert len(files) == 1
