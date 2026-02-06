#!/usr/bin/env python3
"""`osqar checksum` subcommand group."""

from __future__ import annotations

import argparse
from pathlib import Path

from tools.generate_checksums import cli as checksums_cli


def cmd_checksums_generate(args: argparse.Namespace) -> int:
    argv: list[str] = ["--root", str(args.root), "--output", str(args.output)]
    for ex in getattr(args, "exclude", []) or []:
        argv += ["--exclude", str(ex)]
    if getattr(args, "json_report", None):
        argv += ["--json-report", str(args.json_report)]
    return int(checksums_cli(argv))


def cmd_checksums_verify(args: argparse.Namespace) -> int:
    argv: list[str] = ["--root", str(args.root), "--verify", str(args.manifest)]
    for ex in getattr(args, "exclude", []) or []:
        argv += ["--exclude", str(ex)]
    if getattr(args, "json_report", None):
        argv += ["--json-report", str(args.json_report)]
    return int(checksums_cli(argv))


def register(sub: argparse._SubParsersAction) -> None:
    p_sum = sub.add_parser(
        "checksum", help="Generate or verify shipment checksum manifests"
    )
    sum_sub = p_sum.add_subparsers(dest="checksum_cmd", required=True)

    p_gen = sum_sub.add_parser(
        "generate", help="Generate SHA256SUMS for a directory"
    )
    p_gen.add_argument("--root", type=Path, required=True)
    p_gen.add_argument("--output", type=Path, required=True)
    p_gen.add_argument(
        "--exclude", action="append", default=[], help="Exclude glob (repeatable)"
    )
    p_gen.add_argument(
        "--json-report",
        type=Path,
        default=None,
        help="Write machine-readable JSON report to this path",
    )
    p_gen.set_defaults(func=cmd_checksums_generate)

    p_ver = sum_sub.add_parser(
        "verify", help="Verify a directory against SHA256SUMS"
    )
    p_ver.add_argument("--root", type=Path, required=True)
    p_ver.add_argument("--manifest", type=Path, required=True)
    p_ver.add_argument(
        "--exclude", action="append", default=[], help="Exclude glob (repeatable)"
    )
    p_ver.add_argument(
        "--json-report",
        type=Path,
        default=None,
        help="Write machine-readable JSON report to this path",
    )
    p_ver.set_defaults(func=cmd_checksums_verify)
