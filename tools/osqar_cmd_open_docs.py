#!/usr/bin/env python3
"""`osqar open-docs` subcommand."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from tools import osqar_cli_util as u


def cmd_open_docs(args: argparse.Namespace) -> int:
    project = getattr(args, "project", ".")
    shipment = getattr(args, "shipment", None)
    raw_path = getattr(args, "path", None)

    target: Optional[Path] = None

    if raw_path:
        p = u.abspath_no_resolve(Path(raw_path).expanduser())
        if p.is_dir():
            candidate = p / "index.html"
            if candidate.is_file():
                target = candidate
            else:
                print(
                    f"ERROR: index.html not found under directory: {p}",
                    file=sys.stderr,
                )
                return 2
        else:
            target = p
    elif shipment:
        ship_dir = u.abspath_no_resolve(Path(shipment).expanduser())
        target = ship_dir / "index.html"
    else:
        project_dir = u.abspath_no_resolve(Path(project).expanduser())
        ship_dir = u.abspath_no_resolve(project_dir / u.DEFAULT_BUILD_DIR)
        target = ship_dir / "index.html"

    if target is None:
        print("ERROR: could not resolve target path", file=sys.stderr)
        return 2

    if getattr(args, "print_only", False):
        print(target)
        return 0

    if not target.is_file():
        print(
            f"ERROR: documentation entrypoint not found: {target}",
            file=sys.stderr,
        )
        if shipment or raw_path:
            return 2
        print("TIP: build docs first via: osqar build-docs", file=sys.stderr)
        return 2

    return int(u.open_in_browser(target))


def register(sub: argparse._SubParsersAction) -> None:
    p_open = sub.add_parser(
        "open-docs",
        help="Open built HTML documentation (index.html) in your default browser",
    )
    open_group = p_open.add_mutually_exclusive_group(required=False)
    open_group.add_argument(
        "--project",
        default=".",
        help="Project directory (default: .; opens <project>/_build/html/index.html)",
    )
    open_group.add_argument(
        "--shipment", default=None, help="Shipment directory (opens <shipment>/index.html)"
    )
    open_group.add_argument(
        "--path",
        default=None,
        help="HTML file or directory (if directory: opens <dir>/index.html)",
    )
    p_open.add_argument(
        "--print-only", action="store_true", help="Only print the resolved index.html path"
    )
    p_open.set_defaults(func=cmd_open_docs)
