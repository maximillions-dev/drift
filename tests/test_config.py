"""Tests for config parsing and glob matching."""
from pathlib import Path
import tempfile

import yaml

from drift.config import DriftConfig, RuleConfig, glob_match


class TestGlobMatch:
    def test_exact(self):
        assert glob_match("src/main.py", "src/main.py")

    def test_wildcard(self):
        assert glob_match("src/*.py", "src/main.py")
        assert not glob_match("src/*.py", "src/main.rs")

    def test_doublestar_recursive(self):
        assert glob_match("src/**", "src/a/b/c.py")

    def test_doublestar_at_start(self):
        assert glob_match("**/*.py", "foo/bar/baz.py")

    def test_doublestar_in_middle(self):
        assert glob_match("src/**/test.py", "src/a/b/test.py")
        assert glob_match("src/**/test.py", "src/test.py")

    def test_no_match(self):
        assert not glob_match("src/**/*.py", "tests/test.py")

    def test_wildcard_question(self):
        assert glob_match("test?.py", "test1.py")
        assert not glob_match("test?.py", "test12.py")


class TestRuleConfig:
    def test_from_dict_basic(self):
        r = RuleConfig.from_dict({
            "type": "max_lines",
            "rule": "Keep files short",
            "path": "src/**",
            "limit": 500,
        })
        assert r.type == "max_lines"
        assert r.rule == "Keep files short"
        assert r.limit == 500

    def test_from_dict_forbid_import(self):
        r = RuleConfig.from_dict({
            "type": "forbid_import",
            "from": "src/api/**",
            "forbid": ["src/db/**"],
        })
        assert r.type == "forbid_import"
        assert r.from_path == "src/api/**"
        assert r.forbid == ["src/db/**"]

    def test_from_dict_no_circular(self):
        r = RuleConfig.from_dict({
            "type": "no_circular",
            "rule": "No cycles",
            "paths": ["src/**"],
        })
        assert r.type == "no_circular"
        assert r.paths == ["src/**"]

    def test_post_init_syncs_from_and_paths(self):
        r = RuleConfig(type="forbid_import", from_path="src/api/**", paths=[])
        assert r.paths == ["src/api/**"]

        r2 = RuleConfig(type="forbid_import", from_path="", paths=["src/api/**"])
        assert r2.from_path == "src/api/**"


class TestDriftConfig:
    def test_load_nonexistent(self):
        c = DriftConfig.load("/nonexistent/path.yaml")
        assert c.rules == []

    def test_load_valid(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
rules:
  - type: max_lines
    rule: Keep files short
    path: "src/**"
    limit: 500
  - type: forbid_import
    from: "src/api/**"
    forbid: ["src/db/**"]
""")
            p = f.name
        try:
            c = DriftConfig.load(p)
            assert len(c.rules) == 2
            assert c.rules[0].type == "max_lines"
            assert c.rules[0].limit == 500
            assert c.rules[1].type == "forbid_import"
            assert c.rules[1].from_path == "src/api/**"
        finally:
            Path(p).unlink()

    def test_load_empty(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("rules:\n")
            p = f.name
        try:
            c = DriftConfig.load(p)
            assert c.rules == []
        finally:
            Path(p).unlink()
