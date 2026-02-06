#!/usr/bin/env python3
"""`osqar traceability` subcommand."""

from __future__ import annotations

import argparse
from pathlib import Path

from tools.traceability_check import cli as traceability_cli


def cmd_traceability(args: argparse.Namespace) -> int:
    argv: list[str] = [str(args.needs_json)]
    if getattr(args, "json_report", None):
        argv += ["--json-report", str(args.json_report)]

    if getattr(args, "enforce_req_has_test", False):
        argv += ["--enforce-req-has-test"]
    if getattr(args, "enforce_arch_traces_req", False):
        argv += ["--enforce-arch-traces-req"]
    if getattr(args, "enforce_test_traces_req", False):
        argv += ["--enforce-test-traces-req"]

    return int(traceability_cli(argv))


def register(sub: argparse._SubParsersAction) -> None:
    p_tr = sub.add_parser(
        "traceability", help="Run traceability checks on an exported needs.json"
    )
    p_tr.add_argument("needs_json", type=Path, help="Path to needs.json")
    p_tr.add_argument(
        "--json-report", type=Path, default=None, help="Write JSON report to this path"
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
    p_tr.set_defaults(func=cmd_traceability)
