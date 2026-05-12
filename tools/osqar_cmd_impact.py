#!/usr/bin/env python3
"""`osqar impact` — change impact analysis via traceability graph traversal."""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any, Optional

from tools.traceability_check import _load_needs, _collect_trace_links


NEED_TYPE_LABELS: dict[str, str] = {
    "REQ_": "requirement",
    "ARCH_": "architecture",
    "VER_": "verification",
    "TEST_": "test",
    "IMPL_": "implementation",
    "CODE_": "implementation",
    "LM_": "lifecycle",
    "SC_": "safety-case",
}


def _type_label(need_id: str) -> str:
    for prefix, label in NEED_TYPE_LABELS.items():
        if need_id.startswith(prefix):
            return label
    return "need"


def _impact_graph(
    needs_by_id: dict[str, dict[str, Any]],
    seed_id: str,
    *,
    direction: str,
    max_depth: int,
) -> dict[str, Any]:
    """BFS from seed_id following traceability links.

    Returns a tree dict: {need_id: {"need": {...}, "depth": int, "links": [...], "children": {...}}}
    """
    if seed_id not in needs_by_id:
        return {}

    visited: set[str] = set()
    queue: deque[tuple[str, int, Optional[str]]] = deque()
    queue.append((seed_id, 0, None))

    # Build adjacency: forward (links), backward (links_back)
    forward: dict[str, set[str]] = {}
    backward: dict[str, set[str]] = {}
    for nid, need in needs_by_id.items():
        outgoing = _collect_trace_links(need)
        forward[nid] = outgoing
        for target in outgoing:
            backward.setdefault(target, set()).add(nid)

    tree: dict[str, Any] = {}

    while queue:
        nid, depth, parent = queue.popleft()
        if nid in visited:
            continue
        if max_depth is not None and depth > max_depth:
            continue
        visited.add(nid)
        need = needs_by_id.get(nid, {})
        node: dict[str, Any] = {
            "need": {
                "id": nid,
                "title": str(need.get("title", need.get("content", need.get("id", nid)))).strip(),
                "type": _type_label(nid),
                "status": str(need.get("status", "?")),
            },
            "depth": depth,
            "links": [],
        }

        # Gather edges based on direction
        edges: list[str] = []
        if direction in ("downstream", "both"):
            edges.extend(sorted(forward.get(nid, set())))
        if direction in ("upstream", "both"):
            edges.extend(sorted(backward.get(nid, set())))

        node["links"] = sorted(set(edges))
        tree[nid] = node

        for edge in sorted(set(edges)):
            if edge not in visited:
                queue.append((edge, depth + 1, nid))

    # Build parent-child relationships for tree rendering
    children_map: dict[str, list[str]] = {}
    for nid in tree:
        for link in tree[nid]["links"]:
            if link in tree and tree[link]["depth"] == tree[nid]["depth"] + 1:
                children_map.setdefault(nid, []).append(link)

    # Add children to tree nodes
    for nid in tree:
        tree[nid]["children"] = children_map.get(nid, [])

    return tree


def _format_tree(
    tree: dict[str, Any],
    root_id: str,
    *,
    prefix: str = "",
    is_last: bool = True,
) -> list[str]:
    """Render the impact graph as an ASCII tree."""
    lines: list[str] = []
    if root_id not in tree:
        return lines

    node = tree[root_id]
    n = node["need"]
    connector = "└── " if is_last else "├── "
    continuation = "    " if is_last else "│   "

    line = f"{prefix}{connector}{n['id']} ({n['type']}, {n['status']})"
    title = n["title"]
    if title and title != n["id"]:
        max_title = 72
        if len(title) > max_title:
            title = title[: max_title - 1] + "…"
        line += f" — {title}"
    lines.append(line)

    children = node.get("children", [])
    for i, child_id in enumerate(children):
        child_last = i == len(children) - 1
        lines.extend(
            _format_tree(
                tree,
                child_id,
                prefix=prefix + continuation,
                is_last=child_last,
            )
        )

    return lines


def _impact_report_json(tree: dict[str, Any], seed_id: str) -> dict[str, Any]:
    """Build a JSON-serializable impact report."""
    needs_list: list[dict[str, Any]] = []
    type_counts: dict[str, int] = {}
    for nid in sorted(tree):
        n = tree[nid]["need"]
        needs_list.append(n)
        t = n["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "schema": "osqar.impact_report.v1",
        "seed": seed_id,
        "affected_total": len(tree),
        "affected_by_type": type_counts,
        "needs": sorted(needs_list, key=lambda x: (x["type"], x["id"])),
    }


def cmd_impact(args: argparse.Namespace) -> int:
    needs_json: Path = args.needs_json.expanduser().resolve()
    if not needs_json.is_file():
        print(f"ERROR: needs.json not found: {needs_json}", file=sys.stderr)
        return 2

    try:
        needs = _load_needs(needs_json)
    except Exception as exc:
        print(f"ERROR: Failed to read {needs_json}: {exc}", file=sys.stderr)
        return 2

    needs_by_id: dict[str, dict[str, Any]] = {}
    for need in needs:
        nid = str(need.get("id", ""))
        if nid:
            needs_by_id[nid] = need

    seed_id: str = args.need_id.strip()
    if seed_id not in needs_by_id:
        print(f"ERROR: need ID not found in needs.json: {seed_id}", file=sys.stderr)
        return 2

    direction: str = getattr(args, "direction", "both") or "both"
    max_depth: int = int(getattr(args, "max_depth", 0) or 0)
    if max_depth <= 0:
        max_depth = None

    tree = _impact_graph(needs_by_id, seed_id, direction=direction, max_depth=max_depth)

    if not tree:
        print(f"No traceability links found for: {seed_id}")
        return 0

    output_format: str = getattr(args, "format", "tree") or "tree"

    if output_format == "json":
        report = _impact_report_json(tree, seed_id)
        report["direction"] = direction
        if max_depth is not None:
            report["max_depth"] = max_depth

        json_report = getattr(args, "json_report", None)
        if json_report:
            out = Path(json_report).expanduser().resolve()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"Impact report written: {out}")
        else:
            print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    # Tree format (default)
    lines = _format_tree(tree, seed_id, is_last=True)
    print(f"\n{seed_id} ({_type_label(seed_id)})")
    for line in lines:
        print(line)

    # Summary
    type_counts: dict[str, int] = {}
    for nid in tree:
        if nid == seed_id:
            continue
        t = _type_label(nid)
        type_counts[t] = type_counts.get(t, 0) + 1

    affected = len(tree) - 1
    if affected:
        parts = [f"{v} {k}s" for k, v in sorted(type_counts.items())]
        print(f"\nSummary: {affected} affected needs ({', '.join(parts)})")
    else:
        print("\nSummary: no other needs affected")

    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p_impact = sub.add_parser(
        "impact",
        help="Analyze change impact by traversing traceability links",
    )
    p_impact.add_argument(
        "needs_json",
        type=Path,
        help="Path to needs.json or needs.yaml produced by sphinx-needs",
    )
    p_impact.add_argument(
        "--need-id",
        required=True,
        help="Seed need ID to analyze impact for",
    )
    p_impact.add_argument(
        "--direction",
        choices=["downstream", "upstream", "both"],
        default="both",
        help="Traversal direction (default: both)",
    )
    p_impact.add_argument(
        "--max-depth",
        type=int,
        default=0,
        help="Maximum traversal depth (0 = unlimited)",
    )
    p_impact.add_argument(
        "--format",
        choices=["tree", "json"],
        default="tree",
        help="Output format (default: tree)",
    )
    p_impact.add_argument(
        "--json-report",
        type=Path,
        default=None,
        help="Write JSON report to this path (only with --format json)",
    )
    p_impact.set_defaults(func=cmd_impact)
