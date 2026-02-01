#!/usr/bin/env python3
"""Generate and verify checksum manifests for file dumps.

The manifest format is intentionally compatible with common tooling:

<hex>  <relative/path>

- Stable ordering (sorted paths)
- Uses forward slashes
- Defaults to SHA-256

This is designed for compliance/audit evidence bundles where you want to prove
an artifact set has not changed after export.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Entry:
    digest: str
    relpath: str


def _hash_file(path: Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_files(root: Path) -> Iterable[Path]:
    for p in sorted(root.rglob("*")):
        if p.is_file():
            yield p


def _matches_any_glob(relpath: str, globs: list[str]) -> bool:
    # Match both with / and platform separators normalized to /
    rel = relpath.replace("\\", "/")
    return any(fnmatch.fnmatch(rel, g) for g in globs)


def _write_manifest(root: Path, output: Path, algorithm: str, exclude_globs: list[str]) -> list[Entry]:
    root = root.resolve()
    output = output.resolve()

    # Always exclude the output file itself (so the manifest is stable).
    try:
        output_rel = output.relative_to(root).as_posix()
        exclude_globs = exclude_globs + [output_rel]
    except ValueError:
        # Output is outside root; nothing to exclude by relative path.
        pass

    entries: list[Entry] = []
    for file_path in _iter_files(root):
        relpath = file_path.relative_to(root).as_posix()
        if _matches_any_glob(relpath, exclude_globs):
            continue
        entries.append(Entry(digest=_hash_file(file_path, algorithm), relpath=relpath))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(f"{e.digest}  {e.relpath}\n" for e in entries),
        encoding="utf-8",
    )

    return entries


def _read_manifest(manifest: Path) -> list[Entry]:
    entries: list[Entry] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        # Expected: <hex><two spaces><path>
        if "  " not in line:
            raise ValueError(f"Invalid manifest line: {line}")
        digest, relpath = line.split("  ", 1)
        digest = digest.strip()
        relpath = relpath.strip().replace("\\", "/")
        if not digest or not relpath:
            raise ValueError(f"Invalid manifest line: {line}")
        entries.append(Entry(digest=digest, relpath=relpath))
    return entries


def _verify_manifest(root: Path, manifest: Path, algorithm: str) -> tuple[list[str], list[str], list[str]]:
    root = root.resolve()
    entries = _read_manifest(manifest)

    missing: list[str] = []
    mismatched: list[str] = []
    ok: list[str] = []

    for entry in entries:
        file_path = root / entry.relpath
        if not file_path.is_file():
            missing.append(entry.relpath)
            continue
        actual = _hash_file(file_path, algorithm)
        if actual.lower() != entry.digest.lower():
            mismatched.append(entry.relpath)
        else:
            ok.append(entry.relpath)

    return ok, missing, mismatched


def cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate or verify checksum manifests")
    parser.add_argument("--root", type=Path, required=True, help="Root directory to hash")
    parser.add_argument(
        "--algorithm",
        default="sha256",
        help="Hash algorithm supported by hashlib (default: sha256)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=["**/.DS_Store"],
        help="Glob pattern to exclude (repeatable). Default: **/.DS_Store",
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, help="Write manifest file")
    mode.add_argument("--verify", type=Path, help="Verify against existing manifest")

    args = parser.parse_args(argv)

    if not args.root.is_dir():
        print(f"ERROR: root directory not found: {args.root}", file=sys.stderr)
        return 2

    try:
        hashlib.new(args.algorithm)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: unsupported algorithm '{args.algorithm}': {exc}", file=sys.stderr)
        return 2

    if args.output is not None:
        entries = _write_manifest(args.root, args.output, args.algorithm, list(args.exclude))
        print(f"Wrote {len(entries)} checksums to {args.output}")
        return 0

    manifest = args.verify
    if manifest is None or not manifest.is_file():
        print(f"ERROR: manifest not found: {manifest}", file=sys.stderr)
        return 2

    ok, missing, mismatched = _verify_manifest(args.root, manifest, args.algorithm)
    print(f"Verified manifest: ok={len(ok)} missing={len(missing)} mismatched={len(mismatched)}")

    if missing:
        print("Missing files:")
        for p in missing:
            print(f"- {p}")

    if mismatched:
        print("Mismatched files:")
        for p in mismatched:
            print(f"- {p}")

    return 0 if (not missing and not mismatched) else 1


def main() -> int:
    return cli(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
