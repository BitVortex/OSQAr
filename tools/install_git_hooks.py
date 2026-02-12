#!/usr/bin/env python3
"""Install OSQAr repo-local git hooks.

This sets the repository's git config so that hooks live under .githooks/
(tracked in the repo). This provides a consistent contributor experience.

Usage:
  python3 tools/install_git_hooks.py

To bypass hooks for one command (emergencies only):
    OSQAR_SKIP_DOCS_HOOKS=1 git commit ...
    OSQAR_SKIP_DOCS_HOOKS=1 git push
    OSQAR_SKIP_FULL_BUILD_HOOKS=1 git commit ...
    OSQAR_SKIP_FULL_BUILD_HOOKS=1 git push
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    githooks = repo_root / ".githooks"

    if not (repo_root / ".git").exists():
        print("ERROR: not a git checkout (missing .git)", file=sys.stderr)
        return 2

    if not githooks.is_dir():
        print("ERROR: missing .githooks/ directory", file=sys.stderr)
        return 2

    expected = [githooks / "pre-commit", githooks / "pre-push"]
    missing = [p for p in expected if not p.exists()]
    if missing:
        for p in missing:
            print(f"ERROR: missing hook: {p}", file=sys.stderr)
        return 2

    os.chdir(repo_root)

    # Point git to the repo-local hooks directory.
    run(["git", "config", "core.hooksPath", str(githooks)])

    print("Installed git hooks:")
    print("- core.hooksPath = .githooks")
    print("\nHooks enforced locally:")
    print("- .githooks/pre-commit (RST hygiene + framework docs build + all examples)")
    print("- .githooks/pre-push   (RST hygiene + framework docs build + all examples)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
