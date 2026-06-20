"""Circular import detection using DFS."""
from __future__ import annotations

from collections import defaultdict

from drift.config import glob_match
from drift.scanner.base import FileInfo


def find_circular_imports(
    files: list[FileInfo],
    paths: list[str],
    rule_name: str,
) -> list[dict]:
    graph: dict[str, list[str]] = defaultdict(list)
    all_files: set[str] = set()

    for f in files:
        all_files.add(f.relative_path)
        for imp in f.imports:
            if imp.target_file:
                graph[f.relative_path].append(imp.target_file)

    cycles = _find_cycles(graph, all_files, paths)
    violations = []
    for cycle in cycles:
        violations.append({
            "rule": rule_name,
            "type": "circular_import",
            "cycle": cycle,
            "message": " → ".join(cycle),
        })
    return violations


def _find_cycles(
    graph: dict[str, list[str]],
    all_files: set[str],
    path_patterns: list[str],
) -> list[list[str]]:
    relevant = set()
    for f in all_files:
        if any(glob_match(p, f) for p in path_patterns):
            relevant.add(f)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {}
    for node in relevant:
        color[node] = WHITE

    cycles: list[list[str]] = []
    path_stack: list[str] = []

    def dfs(node: str):
        color[node] = GRAY
        path_stack.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in relevant:
                continue
            if color[neighbor] == GRAY:
                cycle_start = path_stack.index(neighbor)
                cycle = path_stack[cycle_start:] + [neighbor]
                cycles.append(cycle)
            elif color[neighbor] == WHITE:
                dfs(neighbor)

        path_stack.pop()
        color[node] = BLACK

    for node in sorted(relevant):
        if color[node] == WHITE:
            dfs(node)

    return _dedup_cycles(cycles)


def _dedup_cycles(cycles: list[list[str]]) -> list[list[str]]:
    seen: set[str] = set()
    unique: list[list[str]] = []
    for cycle in cycles:
        if not cycle:
            continue
        min_idx = cycle.index(min(cycle))
        normalized = cycle[min_idx:] + cycle[1:min_idx]
        key = "|".join(normalized)
        if key not in seen:
            seen.add(key)
            unique.append(normalized)
    return unique
