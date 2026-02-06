#!/usr/bin/env python3
"""OSQAr CLI entrypoint.

The implementation lives in `tools/osqar_cli_app/cli.py`.

Public invocations remain stable:

- `./osqar ...`
- `poetry run python -m tools.osqar_cli ...`
"""

from __future__ import annotations

from tools.osqar_cli_app.cli import build_parser, main

__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
