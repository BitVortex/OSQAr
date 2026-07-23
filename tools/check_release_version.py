"""Fail closed when a release tag does not match the package version."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def read_project_version(pyproject: Path) -> str:
    text = pyproject.read_text(encoding="utf-8")
    section = re.search(r"(?ms)^\[project\]\s*$\n(.*?)(?=^\[|\Z)", text)
    if section is None:
        raise ValueError(f"missing [project] section in {pyproject}")
    version = re.search(
        r'^\s*version\s*=\s*"([^"]+)"\s*$',
        section.group(1),
        flags=re.MULTILINE,
    )
    if version is None:
        raise ValueError(f"missing project version in {pyproject}")
    return version.group(1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True, help="Git release tag to validate")
    parser.add_argument("--pyproject", type=Path, default=Path("pyproject.toml"))
    args = parser.parse_args(argv)

    try:
        version = read_project_version(args.pyproject)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    expected = f"v{version}"
    if args.tag != expected:
        print(
            f"ERROR: release tag {args.tag!r} does not match package version {version!r}; "
            f"expected {expected!r}",
            file=sys.stderr,
        )
        return 2

    print(f"Release metadata matches: tag={args.tag} package={version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
