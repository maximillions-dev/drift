"""Tests for CLI entry point and core functions."""
from pathlib import Path
import tempfile

from drift.main import compute_score, _find_config, scan_directory, cmd_init


class TestComputeScore:
    def test_perfect_score(self):
        assert compute_score(0, 4) == 100

    def test_half_score(self):
        assert compute_score(2, 4) == 50

    def test_zero_rules(self):
        assert compute_score(0, 0) == 100

    def test_all_failing(self):
        assert compute_score(4, 4) == 0

    def test_rounds_down(self):
        assert compute_score(1, 3) == 66


class TestFindConfig:
    def test_dot_drift_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".drift.yaml").write_text("rules: []")
            found = _find_config(root)
            assert found == root / ".drift.yaml"

    def test_drift_yaml_without_dot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "drift.yaml").write_text("rules: []")
            found = _find_config(root)
            assert found == root / "drift.yaml"

    def test_prefers_dot_drift_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".drift.yaml").write_text("rules: []")
            (root / "drift.yaml").write_text("rules: []")
            found = _find_config(root)
            assert found == root / ".drift.yaml"

    def test_no_config_returns_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            found = _find_config(root)
            assert found == root / ".drift.yaml"


class TestCmdInit:
    def test_creates_drift_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cmd_init(root)
            assert (root / ".drift.yaml").exists()
            content = (root / ".drift.yaml").read_text()
            assert "rules:" in content

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".drift.yaml").write_text("existing")
            cmd_init(root)
            assert (root / ".drift.yaml").read_text() == "existing"


class TestScanDirectoryIntegration:
    def test_scans_python_and_javascript(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("import os\n")
            (root / "app.js").write_text("const x = 1;\n")
            files = scan_directory(root)
            assert len(files) == 2
