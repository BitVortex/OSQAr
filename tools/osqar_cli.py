#!/usr/bin/env python3
"""OSQAr CLI entrypoint.

Public invocations remain stable:

- `./osqar ...`
- `poetry run python -m tools.osqar_cli ...`

This file is intentionally low-complexity; it wires subcommands implemented in
standalone scripts under `tools/`.
"""

from __future__ import annotations

import argparse

from tools import osqar_cmd_checksum
from tools import osqar_cmd_code_trace
from tools import osqar_cmd_doctor
from tools import osqar_cmd_framework
from tools import osqar_cmd_new
from tools import osqar_cmd_open_docs
from tools import osqar_cmd_shipment
from tools import osqar_cmd_traceability
from tools import osqar_cmd_workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="osqar", description="OSQAr helper CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # Top-level commands
    osqar_cmd_shipment.register_build_docs_shortcut(sub)
    osqar_cmd_open_docs.register(sub)
    osqar_cmd_doctor.register(sub)
    osqar_cmd_new.register(sub)
    osqar_cmd_traceability.register(sub)
    osqar_cmd_code_trace.register(sub)
    osqar_cmd_checksum.register(sub)
    osqar_cmd_framework.register(sub)

    # Groups
    osqar_cmd_shipment.register(sub)
    osqar_cmd_workspace.register(sub)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
