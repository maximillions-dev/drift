"""drift — Architecture Decay Detector.

Usage:
    drift check [--config=<path>] [--path=<dir>]
    drift diff [<ref>] [--config=<path>] [--path=<dir>]
    drift log [--path=<dir>]
    drift init
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from drift.config import DriftConfig
from drift.reporter import (
    RED,
    GREEN,
    CYAN,
    GRAY,
    RESET,
    _p,
    print_check,
    print_header,
    print_score_history,
    print_summary,
)
from drift.rules.circular_import import find_circular_imports
from drift.rules.file_limits import check_max_files, check_max_lines
from drift.rules.import_rule import check_forbidden_imports
from drift.scanner.base import FileInfo
from drift.scanner.javascript import JavascriptScanner
from drift.scanner.python import PythonScanner


def _find_config(root: Path) -> Path:
    candidates = [root / ".drift.yaml", root / "drift.yaml"]
    for c in candidates:
        if c.exists():
            return c
    return root / ".drift.yaml"


def _scanners():
    return [PythonScanner(), JavascriptScanner()]


def scan_directory(root: Path) -> list[FileInfo]:
    all_files: list[FileInfo] = []
    for scanner in _scanners():
        all_files.extend(scanner.scan_directory(root))
    return all_files


def run_checks(config: DriftConfig, root: Path, files: list[FileInfo]) -> list[dict]:
    """Run all configured rules and return results.
    Returns a flat list of violation dicts.
    """
    results: list[dict] = []

    for rule in config.rules:
        if rule.type == "forbid_import":
            violations = check_forbidden_imports(
                files, rule.paths, rule.forbid, rule.rule
            )
            results.extend(violations)

        elif rule.type == "no_circular":
            violations = find_circular_imports(files, rule.paths, rule.rule)
            results.extend(violations)

        elif rule.type == "max_lines":
            violations = check_max_lines(files, rule.path, rule.limit, rule.rule)
            results.extend(violations)

        elif rule.type == "max_files":
            violations = check_max_files(root, rule.path, rule.limit, rule.rule)
            results.extend(violations)

    return results


def compute_score(violation_count: int, total_rules: int) -> int:
    """Score is per-rule: any violation of a rule counts as 1 fail for that rule.
    But for the display, we show per-rule pass/fail.
    """
    if total_rules == 0:
        return 100
    return max(0, int(100 * (1 - violation_count / total_rules)))


def save_score(root: Path, score: int):
    try:
        subprocess.run(
            ["git", "notes", "--ref", "drift-score", "add", "-m", str(score)],
            cwd=root,
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass


def get_score_history(root: Path) -> list[tuple[str, int]]:
    try:
        result = subprocess.run(
            ["git", "notes", "--ref", "drift-score", "list"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []

        history = []
        for line in result.stdout.strip().split("\n"):
            note_hash = line.split()[0] if " " in line else line
            content = subprocess.run(
                ["git", "notes", "--ref", "drift-score", "show", note_hash],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            date_result = subprocess.run(
                ["git", "log", "-1", "--format=%ad", "--date=short", note_hash],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if content.stdout.strip().isdigit():
                date = date_result.stdout.strip() or "?"
                history.append((date, int(content.stdout.strip())))
        return history
    except Exception:
        return []


def cmd_check(config_path: Path | None, root: Path):
    if config_path is None:
        config_path = _find_config(root)

    config = DriftConfig.load(config_path)

    if not config.rules:
        print(f"  No rules defined in {config_path}")
        print()
        print(f"  Run {CYAN}drift init{RESET} to create a starter config.")
        return

    print_header(f"Scanning {root.name}")
    files = scan_directory(root)
    total_src = len(files)
    print(f"  {total_src} source files found")

    results = run_checks(config, root, files)

    # Per-rule: if a rule has any violations, it fails
    rules_with_violations: set[str] = set()
    by_type: dict[str, list[dict]] = {}
    for v in results:
        rname = v.get("rule", "unknown")
        rules_with_violations.add(rname)
        by_type.setdefault(rname, []).append(v)

    total_rules = len(config.rules)
    failed_rules = len(rules_with_violations)
    passed_rules = total_rules - failed_rules

    print_header("Results")
    if failed_rules == 0:
        print(f"  {GREEN}✓{RESET} All {total_rules} checks passed!")
    else:
        for rname, vlist in by_type.items():
            for v in vlist:
                print_check(v)
        # Show which rules passed
        for rule in config.rules:
            if rule.rule not in rules_with_violations:
                print(f"  {GREEN}✓{RESET} {_p(rule.rule, GRAY)}")

    print_summary(failed_rules, passed_rules, total_rules)

    score = compute_score(failed_rules, total_rules)
    save_score(root, score)


def _count_failed_rules(results: list[dict]) -> set[str]:
    return {v.get("rule", "unknown") for v in results}


def cmd_diff(ref: str, config_path: Path | None, root: Path):
    config_path = config_path or _find_config(root)
    config = DriftConfig.load(config_path)

    if not config.rules:
        print("  No rules defined.")
        return

    print_header(f"Drift diff: HEAD vs {ref}")

    total_rules = len(config.rules)

    current_files = scan_directory(root)
    current_results = run_checks(config, root, current_files)
    current_failed = _count_failed_rules(current_results)
    current_score = compute_score(len(current_failed), total_rules)

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            archive = subprocess.run(
                ["git", "archive", ref, "--format=tar"],
                cwd=root,
                capture_output=True,
                timeout=10,
            )
            subprocess.run(
                ["tar", "xf", "-", "-C", tmpdir],
                input=archive.stdout,
                capture_output=True,
                timeout=10,
            )
            ref_root = Path(tmpdir)
            ref_files = scan_directory(ref_root)
            ref_results = run_checks(config, ref_root, ref_files)
            ref_failed = _count_failed_rules(ref_results)
            ref_score = compute_score(len(ref_failed), total_rules)
        except Exception as e:
            print(f"  {RED}Error comparing with {ref}: {e}{RESET}")
            return

    delta = current_score - ref_score
    color = GREEN if delta >= 0 else RED
    arrow = "↑" if delta >= 0 else "↓"
    print(f"  {ref}: {ref_score}/100")
    print(f"  HEAD: {current_score}/100")
    print(f"  Delta: {color}{arrow} {abs(delta)}{RESET}")

    new_fails = current_failed - ref_failed
    if new_fails:
        print()
        print(f"  {RED}New violations introduced:{RESET}")
        for v in current_results:
            if v.get("rule") in new_fails:
                print_check(v)

    fixed = ref_failed - current_failed
    if fixed:
        print()
        print(f"  {GREEN}Fixed violations:{RESET}")
        for f in fixed:
            print(f"    {GREEN}✓{RESET} {f}")

    print()


def cmd_log(root: Path):
    history = get_score_history(root)
    print_score_history(history)


INIT_CONFIG = """# drift — architecture decay detector
# See https://github.com/maximillions-dev/drift for docs

rules:
  - rule: "API layer must not import database modules directly"
    type: forbid_import
    from: "src/api/**"
    forbid:
      - "src/db/**"
      - "src/models/**"

  - rule: "No circular imports between modules"
    type: no_circular
    paths:
      - "src/**"

  - rule: "Keep source files under 500 lines"
    type: max_lines
    path: "src/**"
    limit: 500

  - rule: "Utils directory should not become a dumping ground"
    type: max_files
    path: "src/utils/**"
    limit: 15
"""


def cmd_init(root: Path):
    config_path = root / ".drift.yaml"
    if config_path.exists():
        print(f"  {RED}.drift.yaml already exists{RESET}")
        return
    config_path.write_text(INIT_CONFIG)
    print(f"  {GREEN}✓{RESET} Created {config_path}")
    print(f"  Run {CYAN}drift check{RESET} to scan your project")


VERSION = "0.1.0"


def main(argv: list[str] | None = None):
    if argv is None:
        argv = sys.argv[1:]

    if not argv or argv[0] in ("--help", "-h", "help"):
        print(__doc__.strip())
        return

    if argv[0] in ("--version", "-V"):
        print(f"drift {VERSION}")
        return

    cmd = argv[0]
    rest = argv[1:]

    root = Path.cwd()
    config_path: Path | None = None
    ref: str | None = None

    if cmd == "diff":
        if rest and not rest[0].startswith("--"):
            ref = rest[0]
            rest = rest[1:]
        else:
            ref = "main"

    i = 0
    while i < len(rest):
        if rest[i] == "--path" and i + 1 < len(rest):
            root = Path(rest[i + 1]).resolve()
            i += 2
        elif rest[i] == "--config" and i + 1 < len(rest):
            config_path = Path(rest[i + 1])
            i += 2
        else:
            i += 1

    if cmd == "check":
        cmd_check(config_path, root)
    elif cmd == "diff":
        cmd_diff(ref or "main", config_path, root)
    elif cmd == "log":
        cmd_log(root)
    elif cmd == "init":
        cmd_init(root)
    else:
        print(f"  Unknown command: {cmd}")
        print(__doc__.strip())


if __name__ == "__main__":
    main()
