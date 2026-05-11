#!/usr/bin/env python3
"""`osqar sign` — cryptographic signature support for shipment manifests."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


SIGNATURE_SUFFIX = ".sig"
GPG_BIN = "gpg"


def _find_gpg() -> str | None:
    gpg = shutil.which(GPG_BIN)
    if gpg:
        return gpg
    # Common alternative names
    for alt in ("gpg2",):
        alt_path = shutil.which(alt)
        if alt_path:
            return alt_path
    return None


def cmd_sign(args: argparse.Namespace) -> int:
    manifest = Path(args.manifest).expanduser().resolve()
    if not manifest.is_file():
        print(f"ERROR: manifest not found: {manifest}", file=sys.stderr)
        return 2

    gpg = _find_gpg()
    if gpg is None:
        print(f"ERROR: {GPG_BIN} not found in PATH. Install gnupg.", file=sys.stderr)
        return 2

    key = getattr(args, "key", None)
    output = Path(args.output) if getattr(args, "output", None) else manifest.with_suffix(manifest.suffix + SIGNATURE_SUFFIX)

    argv = [gpg, "--detach-sign", "--yes"]
    if key:
        argv.extend(["--local-user", str(key)])

    if bool(getattr(args, "armor", False)):
        argv.append("--armor")
        if output.suffix != ".asc":
            output = output.with_suffix(".asc")

    argv.extend(["--output", str(output), str(manifest)])

    try:
        result = subprocess.run(argv, capture_output=True, text=True)
    except FileNotFoundError:
        print(f"ERROR: {gpg} not found", file=sys.stderr)
        return 2

    if result.returncode != 0:
        print(f"ERROR: signing failed (rc={result.returncode})", file=sys.stderr)
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        return 1

    print(f"Signature created: {output}")
    print(f"  manifest: {manifest}")
    if key:
        print(f"  key: {key}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    manifest = Path(args.manifest).expanduser().resolve()
    if not manifest.is_file():
        print(f"ERROR: manifest not found: {manifest}", file=sys.stderr)
        return 2

    gpg = _find_gpg()
    if gpg is None:
        print(f"ERROR: {GPG_BIN} not found in PATH", file=sys.stderr)
        return 2

    signature = (
        Path(args.signature).expanduser().resolve()
        if getattr(args, "signature", None)
        else manifest.with_suffix(manifest.suffix + SIGNATURE_SUFFIX)
    )

    if not signature.is_file():
        print(f"ERROR: signature not found: {signature}", file=sys.stderr)
        return 2

    argv = [gpg, "--verify", str(signature), str(manifest)]
    try:
        result = subprocess.run(argv, capture_output=True, text=True)
    except FileNotFoundError:
        print(f"ERROR: {gpg} not found", file=sys.stderr)
        return 2

    # gpg outputs verification info to stderr
    output = (result.stderr + result.stdout).strip()
    print(output)

    if result.returncode != 0:
        print(f"\nVerification FAILED (rc={result.returncode})")
        return 1

    print("\nVerification OK")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p_sign = sub.add_parser(
        "sign",
        help="Cryptographically sign shipment manifests (GPG detached signature)",
    )
    sign_sub = p_sign.add_subparsers(dest="sign_cmd", required=True)

    p_s = sign_sub.add_parser("sign", help="Create a detached signature")
    p_s.add_argument("--manifest", required=True, help="Path to manifest file (e.g., SHA256SUMS)")
    p_s.add_argument("--key", default=None, help="GPG key ID or email to sign with")
    p_s.add_argument("--output", default=None, help="Output signature path (default: <manifest>.sig)")
    p_s.add_argument("--armor", action="store_true", help="ASCII-armor the signature (.asc)")
    p_s.set_defaults(func=cmd_sign)

    p_v = sign_sub.add_parser("verify", help="Verify a detached signature")
    p_v.add_argument("--manifest", required=True, help="Path to signed manifest file")
    p_v.add_argument("--signature", default=None, help="Path to signature (default: <manifest>.sig)")
    p_v.set_defaults(func=cmd_verify)
