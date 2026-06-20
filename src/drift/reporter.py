"""Terminal reporter — clean, colored output."""
from __future__ import annotations

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _p(text: str, color: str = "", bold: bool = False) -> str:
    prefix = ""
    if bold:
        prefix += BOLD
    if color:
        prefix += color
    if prefix:
        return f"{prefix}{text}{RESET}"
    return text


def print_check(result: dict):
    rule = result.get("rule", "?")
    vtype = result.get("type", "")
    filepath = result.get("file", "")
    line = result.get("line", 0)
    message = result.get("message", "")

    if vtype == "forbidden_import":
        print(f"  {_p('✗', RED)} {_p(rule, CYAN)}")
        print(f"    {_p(filepath, YELLOW)}:{line}")
        print(f"    {_p(message, GRAY)}")

    elif vtype == "circular_import":
        cycle = result.get("cycle", [])
        print(f"  {_p('✗', RED)} {_p(rule, CYAN)}")
        for node in cycle:
            print(f"    {_p(node, YELLOW, bold=True)}")
            if node != cycle[-1]:
                print(f"    {_p('↓', GRAY)}")

    elif vtype in ("max_lines", "max_files"):
        print(f"  {_p('✗', RED)} {_p(rule, CYAN)}")
        print(f"    {_p(filepath, YELLOW)} — {_p(message, GRAY)}")

    else:
        print(f"  {_p('✗', RED)} {_p(rule, CYAN)}")
        print(f"    {_p(filepath, YELLOW)}:{line} — {_p(message, GRAY)}")


def print_header(title: str):
    print(f"\n{_p('─── ', GRAY)}{_p(title, BOLD)}{_p(' ' + '─' * max(0, 50 - len(title)), GRAY)}")


def print_summary(failed: int, passed: int, total: int):
    print()
    print(_p("─" * 55, GRAY))
    if failed == 0:
        print(f"  {_p('✓', GREEN)} All {total} checks passed. Drift score: {_p('100', GREEN, bold=True)}/100")
    else:
        score = max(0, int(100 * (1 - failed / total)))
        color = GREEN if score >= 80 else YELLOW if score >= 50 else RED
        print(f"  {_p('✗', RED)} {failed} rule(s) failed, {passed} passed — "
              f"Drift score: {_p(str(score), color, bold=True)}/100")
        print()
        print(f"  {_p('Hint:', YELLOW)} Fix violations and run {_p('drift check', CYAN)} again.")
        print(f"  Track score history: {_p('drift log', CYAN)}")
    print(_p("─" * 55, GRAY))
    print()


def print_score_history(history: list[tuple[str, int]]):
    print_header("Score History")
    if not history:
        print(f"  {_p('No history yet. Run drift check first.', GRAY)}")
        return
    for date, score in history:
        bar = "█" * max(1, score // 5)
        color = GREEN if score >= 80 else YELLOW if score >= 50 else RED
        print(f"  {_p(date, GRAY)}  {_p(f'{score:>3}', color, bold=True)} {_p(bar, color)}")
    print()
