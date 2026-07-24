"""`osqar release-manifest` closed release-inventory commands."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from tools.release_manifest import (
    generate_release_manifest,
    render_release_description,
    verify_release_manifest,
)


def cmd_generate(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    description = (
        Path(args.description_output).expanduser().resolve()
        if args.description_output is not None
        else None
    )
    exclusions = list(args.exclude or [])
    if description is not None:
        if description == output:
            print("ERROR: manifest and description outputs must be distinct", file=sys.stderr)
            return 2
        if description.exists() and not description.read_text(
            encoding="utf-8", errors="replace"
        ).startswith("# OSQAr verified release inventory\n"):
            print(f"ERROR: refusing to overwrite payload alias: {description}", file=sys.stderr)
            return 2
        try:
            exclusions.append(description.relative_to(root).as_posix())
        except ValueError:
            pass
    output_existed = output.exists()
    description_existed = description.exists() if description is not None else False
    output_owned = False
    description_owned = False
    try:
        payload = generate_release_manifest(
            root=root,
            output=output,
            release_version=str(args.release_version),
            source_revision=str(args.source_revision),
            producer_command=str(args.producer_command),
            tool_version=str(args.tool_version),
            exclusions=exclusions,
        )
        output_owned = not output_existed
        if description is not None:
            from tools.release_manifest import _atomic_write
            _atomic_write(description, render_release_description(payload))
            description_owned = not description_existed
    except (OSError, UnicodeError, ValueError) as exc:
        for stale, owned in ((output, output_owned), (description, description_owned)):
            if stale is not None and owned:
                try:
                    stale.unlink(missing_ok=True)
                except OSError:
                    pass
        print(f"ERROR: failed to generate release manifest: {exc}", file=sys.stderr)
        return 2
    print(f"Release manifest written: {output} ({len(payload['artifacts'])} artifacts)")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    manifest = Path(os.path.abspath(Path(args.manifest).expanduser()))
    report = (
        Path(os.path.abspath(Path(args.report_json).expanduser()))
        if args.report_json is not None
        else None
    )
    if report is not None:
        try:
            report.relative_to(root)
        except ValueError:
            pass
        else:
            print("ERROR: verification report must be outside the shipment root", file=sys.stderr)
            return 2
        alias_error = _report_alias_error(report, manifest, root)
        if alias_error is not None:
            print(f"ERROR: {alias_error}", file=sys.stderr)
            return 2
    result = verify_release_manifest(
        root=root,
        manifest_path=manifest,
        expected_release_version=args.release_version,
        expected_source_revision=args.source_revision,
    )
    if args.report_json is not None:
        from tools.release_manifest import _atomic_write
        _atomic_write(
            report,
            json.dumps(result.as_dict(), indent=2, sort_keys=True) + "\n",
        )
    stream = sys.stdout if result.status == "PASS" else sys.stderr
    print(
        f"Release manifest verification: {result.status} "
        f"(ok={len(result.ok)} missing={len(result.missing)} "
        f"optional-missing={len(result.optional_missing)} "
        f"mismatched={len(result.mismatched)} empty={len(result.empty)} "
        f"unexpected={len(result.unexpected)} errors={len(result.errors)})",
        file=stream,
    )
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 0 if result.status == "PASS" else (2 if result.status == "ERROR" else 1)


def _has_symlink_component(path: Path) -> bool:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            if current.is_symlink():
                return True
        except OSError:
            return True
    return False


def _report_alias_error(report: Path, manifest: Path, root: Path) -> str | None:
    """Reject report aliases before verification or any atomic replacement."""

    if _has_symlink_component(report):
        return f"verification report path must not contain symbolic links: {report}"
    targets = [manifest]
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        for artifact in payload.get("artifacts", []):
            if isinstance(artifact, dict) and isinstance(artifact.get("path"), str):
                targets.append(root / artifact["path"])
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        pass
    report_lexical = os.path.normcase(os.path.abspath(report))
    for target in targets:
        target_lexical = os.path.normcase(os.path.abspath(target))
        if report_lexical == target_lexical:
            return f"verification report must not overwrite manifest or payload: {target}"
        try:
            if report.exists() and target.exists() and os.path.samefile(report, target):
                return f"verification report must not alias manifest or payload: {target}"
        except OSError:
            return f"unable to establish verification report identity: {report}"
    return None


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "release-manifest",
        help="Generate or verify a versioned closed release inventory",
    )
    commands = parser.add_subparsers(dest="release_manifest_cmd", required=True)

    generate = commands.add_parser("generate", help="Generate a closed release manifest")
    generate.add_argument("--root", type=Path, required=True)
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--source-revision", required=True)
    generate.add_argument("--release-version", required=True)
    generate.add_argument("--producer-command", required=True)
    generate.add_argument("--tool-version", required=True)
    generate.add_argument("--exclude", action="append", default=[])
    generate.add_argument("--description-output", type=Path, default=None)
    generate.set_defaults(func=cmd_generate)

    verify = commands.add_parser("verify", help="Verify integrity and exact inventory")
    verify.add_argument("--root", type=Path, required=True)
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--release-version")
    verify.add_argument("--source-revision")
    verify.add_argument("--report-json", type=Path, default=None)
    verify.set_defaults(func=cmd_verify)
