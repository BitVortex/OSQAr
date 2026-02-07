#!/usr/bin/env python3
"""`osqar setup` command.

Goal: make it easy to start working with downloaded OSQAr release assets.

- Verify a sibling checksum file if present
- Extract the ZIP into a directory
- Detect whether it contains a workspace bundle or a shipment
- Run the appropriate verification command

Stdlib-only.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import zipfile
from pathlib import Path

from tools import osqar_cli_util as u
from tools.osqar_cmd_shipment import cmd_shipment_verify
from tools.osqar_cmd_workspace import cmd_workspace_verify


def _warn(msg: str) -> None:
    print(f"WARNING: {msg}", file=sys.stderr)


def _read_sha256sum(path: Path) -> str | None:
    """Parse common sha256sum file formats.

    Expected format is usually:
        <hex>  <filename>
    """

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if not parts:
            continue
        digest = parts[0].strip()
        if len(digest) == 64 and all(c in "0123456789abcdefABCDEF" for c in digest):
            return digest.lower()
        return None

    return None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_optional_checksum(zip_path: Path) -> int:
    candidates = [
        Path(str(zip_path) + ".sha256"),
        Path(str(zip_path) + ".sha256sum"),
        zip_path.with_suffix(".sha256"),
        zip_path.with_suffix(".sha256sum"),
    ]

    checksum_file: Path | None = None
    for c in candidates:
        if c.is_file():
            checksum_file = c
            break

    if checksum_file is None:
        _warn(f"no checksum file found next to archive ({zip_path.name}); continuing")
        return 0

    expected = _read_sha256sum(checksum_file)
    if not expected:
        print(f"ERROR: could not parse SHA256 from: {checksum_file}", file=sys.stderr)
        return 2

    actual = _sha256_file(zip_path)
    if actual != expected:
        print(
            "ERROR: archive checksum mismatch\n"
            f"- archive: {zip_path}\n"
            f"- checksum: {checksum_file}\n"
            f"- expected: {expected}\n"
            f"- actual:   {actual}",
            file=sys.stderr,
        )
        return 2

    print(f"Checksum OK: {checksum_file.name}")
    return 0


def _safe_extract_zip(zf: zipfile.ZipFile, dest: Path) -> None:
    dest = dest.resolve()

    for member in zf.infolist():
        name = member.filename
        if not name or name.endswith("/"):
            continue

        rel = Path(name)
        if rel.is_absolute() or any(part == ".." for part in rel.parts):
            raise ValueError(f"Unsafe path in zip: {name}")

        out_path = (dest / rel).resolve()
        if dest not in out_path.parents and out_path != dest:
            raise ValueError(f"Unsafe path in zip: {name}")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(member, "r") as src, out_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)


def _zip_single_toplevel_dir(zip_path: Path) -> str | None:
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            tops: set[str] = set()
            for name in zf.namelist():
                name = name.strip("/")
                if not name:
                    continue
                top = name.split("/", 1)[0]
                if top:
                    tops.add(top)
            if len(tops) == 1:
                return next(iter(tops))
    except OSError:
        return None
    return None


def _detect_root(extract_dir: Path, zip_path: Path) -> Path:
    top = _zip_single_toplevel_dir(zip_path)
    if top:
        candidate = extract_dir / top
        if candidate.is_dir():
            return candidate
    return extract_dir


def _is_workspace_bundle(root: Path) -> bool:
    return (root / "shipments").is_dir() and (root / u.DEFAULT_CHECKSUM_MANIFEST).is_file()


def _is_shipment_dir(root: Path) -> bool:
    if not (root / u.DEFAULT_CHECKSUM_MANIFEST).is_file():
        return False
    markers = [
        root / "osqar_project.json",
        root / "needs.json",
        root / "index.html",
        root / u.DEFAULT_TRACEABILITY_REPORT,
    ]
    return any(p.is_file() for p in markers)


def cmd_setup(args: argparse.Namespace) -> int:
    zip_path = Path(args.zip).expanduser().resolve()
    if not zip_path.is_file():
        print(f"ERROR: zip archive not found: {zip_path}", file=sys.stderr)
        return 2

    out_dir = Path(args.output).expanduser().resolve() if getattr(args, "output", None) else zip_path.with_suffix("")

    rc = _verify_optional_checksum(zip_path)
    if rc != 0:
        return int(rc)

    if out_dir.exists():
        if not bool(getattr(args, "force", False)):
            print(
                f"ERROR: output directory already exists (use --force to overwrite): {out_dir}",
                file=sys.stderr,
            )
            return 2
        try:
            u.safe_rmtree(out_dir)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            _safe_extract_zip(zf, out_dir)
    except (OSError, zipfile.BadZipFile) as exc:
        print(f"ERROR: failed to extract zip: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    extracted_root = _detect_root(out_dir, zip_path)

    prev_cwd = Path.cwd()
    try:
        os.chdir(extracted_root)

        if _is_workspace_bundle(extracted_root):
            print(f"Extracted workspace to: {extracted_root}")
            print("Running: osqar workspace verify --root .")
            return int(
                cmd_workspace_verify(
                    argparse.Namespace(
                        root=str(extracted_root),
                        config=None,
                        no_hooks=False,
                        verify_command=[],
                        recursive=False,
                        exclude=[],
                        traceability=False,
                        doctor=False,
                        needs_json=None,
                        enforce_req_has_test=False,
                        enforce_arch_traces_req=False,
                        enforce_test_traces_req=False,
                        continue_on_error=False,
                        json_report=None,
                    )
                )
            )

        if _is_shipment_dir(extracted_root):
            print(f"Extracted shipment to: {extracted_root}")
            print("Running: osqar shipment verify --shipment .")
            return int(
                cmd_shipment_verify(
                    argparse.Namespace(
                        shipment=str(extracted_root),
                        config_root=str(extracted_root),
                        config=None,
                        no_hooks=False,
                        verify_command=[],
                        manifest=None,
                        exclude=[],
                        traceability=False,
                        needs_json=None,
                        json_report=None,
                        report_json=None,
                        strict=False,
                        skip_code_trace=False,
                        code_trace_warn_only=False,
                        enforce_no_unknown_ids=False,
                        enforce_req_has_test=False,
                        enforce_arch_traces_req=False,
                        enforce_test_traces_req=False,
                    )
                )
            )

        print(
            "ERROR: extracted bundle does not look like a workspace or a shipment\n"
            f"- extracted_root: {extracted_root}\n"
            "Expected either:\n"
            "- workspace: <root>/shipments/ and <root>/SHA256SUMS\n"
            "- shipment: <root>/SHA256SUMS plus docs/needs/report markers",
            file=sys.stderr,
        )
        return 2
    finally:
        try:
            os.chdir(prev_cwd)
        except OSError:
            pass


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "setup",
        help="Verify, extract, and verify a downloaded shipment/workspace ZIP",
    )
    p.add_argument(
        "zip",
        help="Path to a shipment/workspace .zip (optionally with a sibling .sha256)",
    )
    p.add_argument(
        "--output",
        default=None,
        help="Extraction directory (default: <zip path without .zip>)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output directory if it exists",
    )
    p.set_defaults(func=cmd_setup)


__all__ = ["register", "cmd_setup"]
