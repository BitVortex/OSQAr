#!/usr/bin/env python3
"""`osqar traceability` subcommand."""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

from tools.traceability_check import _load_needs, _collect_trace_links
from tools.traceability_check import cli as traceability_cli


def _need_title(need: dict) -> str:
    """Extract a human-readable title from a need."""
    title = str(need.get("title", need.get("content", ""))).strip()
    if not title:
        title = str(need.get("id", ""))
    # Clean: collapse whitespace, remove embedded newlines
    title = " ".join(title.split())
    return title


def _normalize_links(links: object) -> str:
    """Convert links field to semicolon-delimited string."""
    if links is None:
        return ""
    if isinstance(links, str):
        return links
    if isinstance(links, (list, tuple)):
        return ";".join(str(l) for l in links if l)
    return str(links)


def _export_csv(
    needs_json_path: Path,
    output_path: Path,
    *,
    req_prefixes: tuple[str, ...] = ("REQ_",),
    arch_prefixes: tuple[str, ...] = ("ARCH_",),
    test_prefixes: tuple[str, ...] = ("TEST_", "VER_"),
    code_prefixes: tuple[str, ...] = ("CODE_", "IMPL_"),
    lm_prefixes: tuple[str, ...] = ("LM_",),
) -> int:
    """Export a traceability matrix as CSV from needs.json."""
    try:
        needs = _load_needs(needs_json_path)
    except Exception as exc:
        print(f"ERROR: Failed to read {needs_json_path}: {exc}")
        return 2

    if not needs:
        print("WARNING: no needs found in needs.json")
        return 1

    # Build lookup
    needs_by_id: dict[str, dict] = {str(n.get("id", "")): n for n in needs if n.get("id")}
    all_ids = set(needs_by_id)

    # Identify requirements (rows) and all linked types (columns)
    req_rows: list[dict] = []
    for nid, need in sorted(needs_by_id.items()):
        if nid.startswith(req_prefixes):
            req_rows.append(need)

    if not req_rows:
        print("WARNING: no requirements found (check --req-prefix)")
        return 1

    # CSV columns
    fieldnames = [
        "REQ_ID",
        "REQ_Title",
        "Status",
        "Tags",
        "ARCH_Linked",
        "VER_Linked",
        "IMPL_Linked",
        "LM_Linked",
        "Other_Linked",
        "Total_Links",
    ]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for req in req_rows:
        nid = str(req.get("id", ""))
        linked = _collect_trace_links(req)

        # Classify links by target prefix
        arch_links: list[str] = []
        ver_links: list[str] = []
        impl_links: list[str] = []
        lm_links: list[str] = []
        other_links: list[str] = []

        for target in sorted(linked):
            if not target:
                continue
            if target in all_ids and target not in needs_by_id:
                continue  # dead link — skip
            if target.startswith(arch_prefixes):
                arch_links.append(target)
            elif target.startswith(test_prefixes):
                ver_links.append(target)
            elif target.startswith(code_prefixes):
                impl_links.append(target)
            elif target.startswith(lm_prefixes):
                lm_links.append(target)
            else:
                other_links.append(target)

        tags = req.get("tags")
        if isinstance(tags, list):
            tags_str = ";".join(str(t) for t in tags if t)
        elif isinstance(tags, str):
            tags_str = tags
        else:
            tags_str = ""

        row = {
            "REQ_ID": nid,
            "REQ_Title": _need_title(req),
            "Status": str(req.get("status", "")),
            "Tags": tags_str,
            "ARCH_Linked": ";".join(arch_links),
            "VER_Linked": ";".join(ver_links),
            "IMPL_Linked": ";".join(impl_links),
            "LM_Linked": ";".join(lm_links),
            "Other_Linked": ";".join(other_links),
            "Total_Links": str(len(linked)),
        }
        writer.writerow(row)

    csv_text = buf.getvalue()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(csv_text, encoding="utf-8")

    print(f"Traceability matrix written: {output_path}")
    print(f"  {len(req_rows)} requirements, CSV columns: {', '.join(fieldnames)}")
    return 0


def cmd_traceability(args: argparse.Namespace) -> int:
    # CSV export mode
    fmt = getattr(args, "format", None)
    if fmt == "csv":
        output = getattr(args, "format_output", None)
        if not output:
            print("ERROR: --format-output is required with --format csv", __import__("sys").stderr)
            return 2
        output_path = Path(output).expanduser().resolve()
        return _export_csv(
            Path(str(args.needs_json)).expanduser().resolve(),
            output_path,
            req_prefixes=tuple(getattr(args, "req_prefix", []) or ["REQ_"]),
            arch_prefixes=tuple(getattr(args, "arch_prefix", []) or ["ARCH_"]),
            test_prefixes=tuple(getattr(args, "test_prefix", []) or ["TEST_", "VER_"]),
            code_prefixes=tuple(getattr(args, "code_prefix", []) or ["CODE_", "IMPL_"]),
            lm_prefixes=tuple(getattr(args, "lm_prefix", []) or ["LM_"]),
        )

    # Standard traceability check
    argv: list[str] = [str(args.needs_json)]
    if getattr(args, "json_report", None):
        argv += ["--json-report", str(args.json_report)]

    for prefix_attr in ("req_prefix", "arch_prefix", "test_prefix", "code_prefix"):
        values = getattr(args, prefix_attr, None) or []
        flag = "--" + prefix_attr.replace("_", "-")
        for v in values:
            argv.extend([flag, str(v)])

    if getattr(args, "enforce_req_has_test", False):
        argv += ["--enforce-req-has-test"]
    if getattr(args, "enforce_arch_traces_req", False):
        argv += ["--enforce-arch-traces-req"]
    if getattr(args, "enforce_test_traces_req", False):
        argv += ["--enforce-test-traces-req"]

    return int(traceability_cli(argv))


def register(sub: argparse._SubParsersAction) -> None:
    p_tr = sub.add_parser(
        "traceability", help="Run traceability checks or export traceability matrix"
    )
    p_tr.add_argument("needs_json", type=Path, help="Path to needs.json")
    p_tr.add_argument(
        "--json-report", type=Path, default=None, help="Write JSON report to this path"
    )
    p_tr.add_argument(
        "--format",
        choices=["csv"],
        default="check",
        help="Output mode: 'check' (default) for violations, 'csv' for traceability matrix export",
    )
    p_tr.add_argument(
        "--format-output",
        type=Path,
        default=None,
        help="File to write when using --format csv (required for CSV)",
    )
    p_tr.add_argument(
        "--enforce-req-has-test",
        action="store_true",
        help="Also enforce REQ_* → TEST_* coverage",
    )
    p_tr.add_argument(
        "--enforce-arch-traces-req",
        action="store_true",
        help="Also enforce ARCH_* → REQ_* coverage",
    )
    p_tr.add_argument(
        "--enforce-test-traces-req",
        action="store_true",
        help="Also enforce TEST_* → REQ_* coverage",
    )
    p_tr.add_argument(
        "--req-prefix",
        action="append",
        default=[],
        help="Requirement ID prefix (repeatable; default: REQ_)",
    )
    p_tr.add_argument(
        "--arch-prefix",
        action="append",
        default=[],
        help="Architecture ID prefix (repeatable; default: ARCH_)",
    )
    p_tr.add_argument(
        "--test-prefix",
        action="append",
        default=[],
        help="Test ID prefix (repeatable; default: TEST_)",
    )
    p_tr.add_argument(
        "--code-prefix",
        action="append",
        default=[],
        help="Implementation/code ID prefix (repeatable; default: CODE_, IMPL_)",
    )
    p_tr.add_argument(
        "--lm-prefix",
        action="append",
        default=[],
        help="Lifecycle management ID prefix (repeatable; default: LM_)",
    )
    p_tr.set_defaults(func=cmd_traceability)
