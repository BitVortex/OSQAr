#!/usr/bin/env python3
"""`osqar code-trace` subcommand."""

from __future__ import annotations

import argparse
from pathlib import Path

from tools.code_trace_check import cli as code_trace_cli


def cmd_code_trace(args: argparse.Namespace) -> int:
    argv: list[str] = ["--root", str(args.root)]
    if getattr(args, "needs_json", None):
        argv += ["--needs-json", str(args.needs_json)]
    if getattr(args, "json_report", None):
        argv += ["--json-report", str(args.json_report)]

    for d in getattr(args, "impl_dir", []) or []:
        argv += ["--impl-dir", str(d)]
    for d in getattr(args, "test_dir", []) or []:
        argv += ["--test-dir", str(d)]
    for ex in getattr(args, "exclude", []) or []:
        argv += ["--exclude", str(ex)]
    for ext in getattr(args, "ext", []) or []:
        argv += ["--ext", str(ext)]
    if getattr(args, "max_bytes", None) is not None:
        argv += ["--max-bytes", str(args.max_bytes)]

    if getattr(args, "enforce_req_in_impl", False):
        argv += ["--enforce-req-in-impl"]
    if getattr(args, "enforce_arch_in_impl", False):
        argv += ["--enforce-arch-in-impl"]
    if getattr(args, "enforce_test_in_tests", False):
        argv += ["--enforce-test-in-tests"]
    if getattr(args, "enforce_no_unknown_ids", False):
        argv += ["--enforce-no-unknown-ids"]

    return int(code_trace_cli(argv))


def register(sub: argparse._SubParsersAction) -> None:
    p_ct = sub.add_parser(
        "code-trace",
        help=(
            "Scan implementation/tests for need IDs in comments and optionally enforce coverage against needs.json"
        ),
    )
    p_ct.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Project root directory to scan (default: .)",
    )
    p_ct.add_argument(
        "--needs-json",
        type=Path,
        default=None,
        help="Optional needs.json to define expected REQ_/ARCH_/TEST_ IDs",
    )
    p_ct.add_argument(
        "--json-report",
        type=Path,
        default=None,
        help="Write machine-readable JSON report to this path",
    )
    p_ct.add_argument(
        "--impl-dir",
        action="append",
        default=[],
        help="Implementation directory/file relative to --root (repeatable; default: auto-detect)",
    )
    p_ct.add_argument(
        "--test-dir",
        action="append",
        default=[],
        help="Test directory/file relative to --root (repeatable; default: auto-detect)",
    )
    p_ct.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude glob(s) relative to --root (repeatable)",
    )
    p_ct.add_argument(
        "--ext",
        action="append",
        default=[],
        help="File extension to scan, including leading dot (repeatable)",
    )
    p_ct.add_argument(
        "--max-bytes",
        type=int,
        default=2_000_000,
        help="Skip files larger than this many bytes (default: 2000000)",
    )
    p_ct.add_argument(
        "--enforce-req-in-impl",
        action="store_true",
        help="Fail if any REQ_* from needs.json is not found in implementation sources",
    )
    p_ct.add_argument(
        "--enforce-arch-in-impl",
        action="store_true",
        help="Fail if any ARCH_* from needs.json is not found in implementation sources",
    )
    p_ct.add_argument(
        "--enforce-test-in-tests",
        action="store_true",
        help="Fail if any TEST_* from needs.json is not found in test sources",
    )
    p_ct.add_argument(
        "--enforce-no-unknown-ids",
        action="store_true",
        help="Fail if code mentions IDs that are not present in needs.json",
    )
    p_ct.set_defaults(func=cmd_code_trace)
