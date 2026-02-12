#!/usr/bin/env python3
"""Fix reStructuredText section title underline/overline lengths.

Sphinx can emit warnings like:

  WARNING: Title underline too short.

This script finds common reST title patterns and ensures the underline (and
matching overline, if present) is at least as long as the title text.

It is intentionally conservative:
- Only adjusts lines that look like title adornment lines (repeated single char).
- Only extends adornment; it does not shorten lines.
- Operates only on top-level (non-indented) titles to avoid touching code blocks.
- Preserves adornment character.

Typical usage:
    python3 tools/fix_rst_title_underlines.py --write docs index.rst
    python3 tools/fix_rst_title_underlines.py --check .

Exit codes:
  0: success (and no changes needed in --check)
  1: changes would be made (only in --check)
  2: invalid usage / file errors
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


_ADORN_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<char>[^\w\s])(?P<run>(?P=char){2,})[ \t]*$")


@dataclass(frozen=True)
class Change:
    path: Path
    line_no: int
    old: str
    new: str


def _iter_rst_files(inputs: list[Path]) -> Iterator[Path]:
    for p in inputs:
        if p.is_dir():
            yield from sorted(p.rglob("*.rst"))
        else:
            if p.suffix.lower() == ".rst":
                yield p


def _split_keepends(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def _match_adornment(line: str) -> tuple[str, str, int] | None:
    # Work with the line without the trailing newline, but keep indentation.
    raw = line.rstrip("\n")
    m = _ADORN_RE.match(raw)
    if not m:
        return None
    indent = m.group("indent")
    # Safety: avoid modifying code blocks / literal examples.
    # OSQAr titles are expected to be flush-left.
    if indent:
        return None
    char = m.group("char")
    # Regex captures the first adornment character in "char" and the remaining
    # repeated run in "run".
    run_len = 1 + len(m.group("run"))
    return indent, char, run_len


def _title_text_for(indent: str, title_line: str) -> str | None:
    # Title lines usually match the indentation of their adornment.
    raw = title_line.rstrip("\n")
    if not raw.strip():
        return None
    if not raw.startswith(indent):
        return None
    title = raw[len(indent) :].rstrip()
    if not title:
        return None
    # Avoid mistaking literal blocks / directives as titles.
    stripped = title.lstrip()
    if stripped.startswith(".. "):
        return None
    if stripped.startswith(":") and stripped.endswith("::"):
        return None
    return title


def fix_file(path: Path) -> tuple[list[str], list[Change]]:
    original = path.read_text(encoding="utf-8")
    lines = _split_keepends(original)

    changes: list[Change] = []

    # Iterate over possible title + underline pairs.
    for i in range(0, len(lines) - 1):
        underline = _match_adornment(lines[i + 1])
        if underline is None:
            continue

        indent, char, underline_len = underline
        title = _title_text_for(indent, lines[i])
        if title is None:
            continue

        needed = len(title)
        if underline_len < needed:
            old = lines[i + 1]
            nl = "\n" if old.endswith("\n") else ""
            lines[i + 1] = f"{indent}{char * needed}{nl}"
            changes.append(Change(path=path, line_no=i + 2, old=old, new=lines[i + 1]))

        # Also fix overline if present and matching.
        if i - 1 >= 0:
            overline = _match_adornment(lines[i - 1])
            if overline is not None:
                o_indent, o_char, o_len = overline
                if o_indent == indent and o_char == char:
                    if o_len < needed:
                        old = lines[i - 1]
                        nl = "\n" if old.endswith("\n") else ""
                        lines[i - 1] = f"{indent}{char * needed}{nl}"
                        changes.append(Change(path=path, line_no=i, old=old, new=lines[i - 1]))

    return lines, changes


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(Path.cwd()))
    except Exception:
        return str(p)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="+",
        help="Files or directories to scan (directories searched recursively for *.rst)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write changes; exit with code 1 if any file would change.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write changes back to disk (default if neither --check nor --write given).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every modified line.",
    )

    ns = parser.parse_args(argv)

    # Default behavior is to write fixes (since the tool is a fixer).
    do_write = ns.write or not ns.check

    inputs = [Path(p) for p in ns.paths]
    files = list(_iter_rst_files(inputs))
    if not files:
        print("No .rst files found in the provided paths.", file=sys.stderr)
        return 2

    any_changes = False

    for f in files:
        try:
            new_lines, changes = fix_file(f)
        except OSError as e:
            print(f"ERROR: failed reading {f}: {e}", file=sys.stderr)
            return 2

        if not changes:
            continue

        any_changes = True
        if ns.verbose:
            for c in changes:
                old = c.old.rstrip("\n")
                new = c.new.rstrip("\n")
                print(f"{_rel(c.path)}:{c.line_no}: {old!r} -> {new!r}")
        else:
            action = "Fixing" if do_write else "Would fix"
            print(f"{action} {_rel(f)} ({len(changes)} change(s))")

        if do_write:
            try:
                f.write_text("".join(new_lines), encoding="utf-8")
            except OSError as e:
                print(f"ERROR: failed writing {f}: {e}", file=sys.stderr)
                return 2

    if ns.check and any_changes:
        print("Title underline fixes needed. Re-run with --write.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
