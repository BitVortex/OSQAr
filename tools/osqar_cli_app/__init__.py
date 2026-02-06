"""OSQAr CLI implementation package.

This package hosts the CLI implementation that is invoked via the repo wrappers
(`./osqar`, `osqar.cmd`, `osqar.ps1`).
"""

from __future__ import annotations

from .cli import build_parser, main

__all__ = ["build_parser", "main"]
