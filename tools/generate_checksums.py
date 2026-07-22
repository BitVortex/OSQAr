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
import json
import os
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


@dataclass(frozen=True)
class Entry:
    digest: str
    relpath: str


class ChecksumReportError(ValueError):
    """Raised when a requested JSON report cannot be safely published."""


def _invalidate_json_report(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        raise ChecksumReportError(f"cannot invalidate JSON report: {exc}") from exc


def _poison_json_output(stream: object | None, descriptor: int | None, path: Path) -> str | None:
    marker = "INVALID JSON REPORT - PUBLICATION FAILED\n"
    errors: list[str] = []
    if stream is not None:
        try:
            stream.seek(0)  # type: ignore[attr-defined]
            stream.truncate(0)  # type: ignore[attr-defined]
            stream.write(marker)  # type: ignore[attr-defined]
            stream.flush()  # type: ignore[attr-defined]
            os.fsync(stream.fileno())  # type: ignore[attr-defined]
            return None
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            errors.append(str(exc))
    if descriptor is not None:
        try:
            os.lseek(descriptor, 0, os.SEEK_SET)
            os.ftruncate(descriptor, 0)
            os.write(descriptor, marker.encode("utf-8"))
            os.fsync(descriptor)
            return None
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            errors.append(str(exc))
    try:
        fallback = os.open(path, os.O_WRONLY | os.O_TRUNC)
        try:
            os.write(fallback, marker.encode("utf-8"))
            os.fsync(fallback)
        finally:
            os.close(fallback)
        return None
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return "; ".join(errors)


def _close_json_output(stream: object | None, descriptor: int | None) -> None:
    if stream is not None:
        close = getattr(stream, "close", None)
        if close is None:
            close = getattr(getattr(stream, "stream", None), "close", None)
        if close is not None:
            close()
    elif descriptor is not None:
        os.close(descriptor)


def _write_text_atomic(path: Path, content: str, artifact_name: str) -> None:
    """Publish text without exposing a partial final pathname."""
    temporary: Path | None = None
    descriptor: int | None = None
    stream: object | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        )
        temporary = Path(temporary_name)
        stream = os.fdopen(descriptor, "w", encoding="utf-8")
        descriptor = None
        stream.write(content)  # type: ignore[attr-defined]
        stream.flush()  # type: ignore[attr-defined]
        os.fsync(stream.fileno())  # type: ignore[attr-defined]
        # Close before replacement so a close fault cannot displace the prior
        # final manifest. Replacement is the final fallible publication step.
        _close_json_output(stream, descriptor)
        stream = None
        os.replace(temporary, path)
        temporary = None
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        cleanup_path = temporary
        cleanup_exc: OSError | None = None
        if cleanup_path is not None:
            try:
                cleanup_path.unlink(missing_ok=True)
            except OSError as unlink_exc:
                cleanup_exc = unlink_exc
        poison_error = None
        if cleanup_exc is not None and cleanup_path is not None:
            poison_error = _poison_json_output(stream, descriptor, cleanup_path)
        try:
            _close_json_output(stream, descriptor)
        except OSError:
            pass
        message = f"cannot write {artifact_name}: {exc}"
        if cleanup_exc is not None:
            message += f"; temporary cleanup failed: {cleanup_exc}"
        if poison_error is not None:
            message += f"; temporary invalidation failed: {poison_error}"
        raise OSError(message) from exc


def _write_json_report(path: Path, payload: dict[str, object]) -> None:
    temporary: Path | None = None
    descriptor: int | None = None
    stream: object | None = None
    published = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        )
        temporary = Path(temporary_name)
        stream = os.fdopen(descriptor, "w", encoding="utf-8")
        descriptor = None
        stream.write(serialized)  # type: ignore[attr-defined]
        stream.flush()  # type: ignore[attr-defined]
        os.fsync(stream.fileno())  # type: ignore[attr-defined]
        os.replace(temporary, path)
        published = True
        temporary = None
        _close_json_output(stream, descriptor)
        stream = None
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        cleanup_path = path if published else temporary
        cleanup_exc: OSError | None = None
        if cleanup_path is not None:
            try:
                cleanup_path.unlink(missing_ok=True)
            except OSError as unlink_exc:
                cleanup_exc = unlink_exc
        poison_error = None
        if cleanup_exc is not None and cleanup_path is not None:
            poison_error = _poison_json_output(stream, descriptor, cleanup_path)
        try:
            _close_json_output(stream, descriptor)
        except OSError:
            pass
        message = f"cannot write JSON report: {exc}"
        if cleanup_exc is not None:
            message += f"; temporary cleanup failed: {cleanup_exc}"
        if poison_error is not None:
            message += f"; temporary invalidation failed: {poison_error}"
        raise ChecksumReportError(message) from exc


def _hash_file(path: Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_files(root: Path) -> Iterable[Path]:
    root = root.resolve()
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise ValueError(f"Symlinked artifact is not permitted: {p.relative_to(root)}")
        if p.is_file():
            try:
                p.resolve().relative_to(root)
            except ValueError as exc:
                raise ValueError(
                    f"Artifact resolves outside root: {p.relative_to(root)}"
                ) from exc
            yield p


def _reject_symlinked_path(root: Path, path: Path, relpath: str) -> None:
    """Reject a declared artifact reached through any symlink component."""
    current = root
    for part in PurePosixPath(relpath).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Symlinked artifact is not permitted: {relpath}")
    try:
        path.resolve().relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Artifact resolves outside root: {relpath}") from exc


def _matches_any_glob(relpath: str, globs: list[str]) -> bool:
    # Match both with / and platform separators normalized to /
    rel = relpath.replace("\\", "/")
    return any(fnmatch.fnmatch(rel, g) for g in globs)


def _write_manifest(
    root: Path, output: Path, algorithm: str, exclude_globs: list[str]
) -> list[Entry]:
    root = root.resolve()
    if output.is_symlink():
        raise ValueError(f"Checksum manifest output must not be a symlink: {output}")
    if output.exists():
        output_status = output.lstat()
        if not stat.S_ISREG(output_status.st_mode) or output_status.st_nlink != 1:
            raise ValueError(
                "Checksum manifest output must be a single-link regular file: "
                f"{output}"
            )
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

    if not entries:
        raise ValueError("Cannot generate checksum manifest with no entries")

    _write_text_atomic(
        output,
        "".join(f"{e.digest}  {e.relpath}\n" for e in entries),
        "checksum manifest",
    )

    return entries


def _read_manifest(manifest: Path, algorithm: str) -> list[Entry]:
    entries: list[Entry] = []
    seen: set[str] = set()
    digest_length = hashlib.new(algorithm).digest_size * 2
    for line_number, line in enumerate(
        manifest.read_text(encoding="utf-8").splitlines(), 1
    ):
        line = line.strip()
        if not line:
            continue
        if "  " not in line:
            raise ValueError(f"Invalid manifest line {line_number}: {line}")
        digest, relpath = line.split("  ", 1)
        digest = digest.strip()
        relpath = relpath.strip().replace("\\", "/")
        if not digest or not relpath:
            raise ValueError(f"Invalid manifest line {line_number}: {line}")
        if len(digest) != digest_length or any(
            c not in "0123456789abcdefABCDEF" for c in digest
        ):
            raise ValueError(f"Invalid {algorithm} digest on manifest line {line_number}")
        pure_path = PurePosixPath(relpath)
        if pure_path.is_absolute() or ".." in pure_path.parts or relpath in {".", ""}:
            raise ValueError(f"Manifest path must be relative and contained: {relpath}")
        normalized = pure_path.as_posix()
        if normalized in seen:
            raise ValueError(f"Duplicate manifest path: {normalized}")
        seen.add(normalized)
        entries.append(Entry(digest=digest, relpath=normalized))
    if not entries:
        raise ValueError("Manifest contains no entries")
    return entries


def _verify_manifest(
    root: Path,
    manifest: Path,
    algorithm: str,
    *,
    closed_set: bool = False,
    exclude_globs: list[str] | None = None,
    exclude_paths: set[Path] | None = None,
) -> tuple[list[str], list[str], list[str], list[str]]:
    root = root.resolve()
    if manifest.is_symlink():
        raise ValueError(f"Checksum manifest must not be a symlink: {manifest}")
    manifest = manifest.resolve()
    entries = _read_manifest(manifest, algorithm)

    missing: list[str] = []
    mismatched: list[str] = []
    ok: list[str] = []

    for entry in entries:
        file_path = root / entry.relpath
        _reject_symlinked_path(root, file_path, entry.relpath)
        if not file_path.is_file():
            missing.append(entry.relpath)
            continue
        actual = _hash_file(file_path, algorithm)
        if actual.lower() != entry.digest.lower():
            mismatched.append(entry.relpath)
        else:
            ok.append(entry.relpath)

    unexpected: list[str] = []
    if closed_set:
        excluded = list(exclude_globs or [])
        resolved_excluded_paths = {path.resolve() for path in (exclude_paths or set())}
        try:
            excluded.append(manifest.relative_to(root).as_posix())
        except ValueError:
            pass
        declared = {entry.relpath for entry in entries}
        actual_paths = {
            path.relative_to(root).as_posix()
            for path in _iter_files(root)
            if path.resolve() not in resolved_excluded_paths
            and not _matches_any_glob(path.relative_to(root).as_posix(), excluded)
        }
        unexpected = sorted(actual_paths - declared)

    return ok, missing, mismatched, unexpected


def cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Generate or verify checksum manifests"
    )
    parser.add_argument(
        "--root", type=Path, required=True, help="Root directory to hash"
    )
    parser.add_argument(
        "--algorithm",
        default="sha256",
        help="Hash algorithm supported by hashlib (default: sha256)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[
            "**/.DS_Store",
            "**/__pycache__/**",
            "**/*.pyc",
            "**/.pytest_cache/**",
            "**/.mypy_cache/**",
            "**/.ruff_cache/**",
        ],
        help=(
            "Glob pattern to exclude (repeatable). "
            "Defaults exclude common transient files (e.g., **/.DS_Store, **/__pycache__/**, **/*.pyc)."
        ),
    )
    parser.add_argument(
        "--json-report",
        type=Path,
        default=None,
        help=(
            "Optional path to write a machine-readable JSON report "
            "(recommended for CI / large workspaces)"
        ),
    )
    parser.add_argument(
        "--closed-set",
        action="store_true",
        help="Reject regular files not declared by the manifest (verification only)",
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, help="Write manifest file")
    mode.add_argument("--verify", type=Path, help="Verify against existing manifest")

    args = parser.parse_args(argv)

    try:
        algorithm = hashlib.new(args.algorithm)
        if algorithm.digest_size <= 0:
            raise ValueError("variable-length digest algorithms are not supported")
    except Exception as exc:  # noqa: BLE001
        print(
            f"ERROR: unsupported algorithm '{args.algorithm}': {exc}", file=sys.stderr
        )
        return 2

    resolved_json_report: Path | None = None
    if args.json_report is not None:
        try:
            root_resolved = args.root.resolve()
            resolved_json_report = args.json_report.resolve()
            selected_manifest = args.output if args.output is not None else args.verify
            assert selected_manifest is not None
            resolved_manifest = selected_manifest.resolve()
            if resolved_json_report == resolved_manifest or (
                args.json_report.exists()
                and selected_manifest.exists()
                and args.json_report.samefile(selected_manifest)
            ):
                message = (
                    "ERROR: JSON report and manifest output resolve to the same path"
                    if args.output is not None
                    else "ERROR: JSON report resolves to the checksum manifest"
                )
                print(message, file=sys.stderr)
                return 2

            preflight_entries: list[Entry] | None = None
            if args.verify is not None:
                try:
                    preflight_entries = _read_manifest(args.verify, args.algorithm)
                except (OSError, UnicodeError, ValueError):
                    # Preserve stale-report invalidation for malformed inputs. The
                    # authoritative parser below will report the original error.
                    preflight_entries = None
                if preflight_entries is not None:
                    for entry in preflight_entries:
                        artifact = root_resolved / entry.relpath
                        if artifact.resolve() == resolved_json_report or (
                            args.json_report.exists()
                            and artifact.exists()
                            and artifact.samefile(args.json_report)
                        ):
                            print(
                                "ERROR: JSON report resolves to "
                                f"manifest-declared artifact: {entry.relpath}",
                                file=sys.stderr,
                            )
                            return 2

            if args.json_report.is_symlink():
                print("ERROR: JSON report output must not be a symlink", file=sys.stderr)
                return 2
            if args.json_report.exists():
                report_status = args.json_report.lstat()
                if (
                    not stat.S_ISREG(report_status.st_mode)
                    or report_status.st_nlink != 1
                ):
                    print(
                        "ERROR: JSON report output must be a single-link regular file",
                        file=sys.stderr,
                    )
                    return 2

            prior_report_matches = False
            if args.json_report.exists():
                try:
                    prior_payload = json.loads(
                        args.json_report.read_text(encoding="utf-8")
                    )
                    prior_report_matches = (
                        isinstance(prior_payload, dict)
                        and prior_payload.get("schema") == "osqar.checksums_report.v1"
                        and prior_payload.get("root") == str(root_resolved)
                        and prior_payload.get("manifest") == str(resolved_manifest)
                    )
                except (OSError, UnicodeError, ValueError):
                    prior_report_matches = False

            if args.root.is_dir():
                for artifact in _iter_files(root_resolved):
                    if args.json_report.exists() and artifact.samefile(args.json_report):
                        if (
                            artifact.resolve() != resolved_json_report
                            or not prior_report_matches
                        ):
                            print(
                                "ERROR: JSON report aliases existing root artifact: "
                                f"{artifact.relative_to(root_resolved).as_posix()}",
                                file=sys.stderr,
                            )
                            return 2
        except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
            print(f"ERROR: cannot preflight checksum paths: {exc}", file=sys.stderr)
            return 2
        try:
            _invalidate_json_report(args.json_report)
        except ChecksumReportError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    if not args.root.is_dir():
        print(f"ERROR: root directory not found: {args.root}", file=sys.stderr)
        return 2

    if args.output is not None:
        generation_excludes = list(args.exclude)
        if resolved_json_report is not None:
            try:
                generation_excludes.append(
                    resolved_json_report.relative_to(args.root.resolve()).as_posix()
                )
            except ValueError:
                pass
        try:
            entries = _write_manifest(
                args.root, args.output, args.algorithm, generation_excludes
            )
        except (OSError, UnicodeError, ValueError) as exc:
            print(f"ERROR: cannot generate checksum manifest: {exc}", file=sys.stderr)
            return 2
        print(f"Wrote {len(entries)} checksums to {args.output}")

        if args.json_report is not None:
            report = {
                "schema": "osqar.checksums_report.v1",
                "mode": "generate",
                "root": str(args.root.resolve()),
                "manifest": str(args.output.resolve()),
                "algorithm": str(args.algorithm),
                "excluded": list(args.exclude),
                "counts": {
                    "entries_total": len(entries),
                },
            }
            try:
                _write_json_report(args.json_report, report)
            except ChecksumReportError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 2
        return 0

    manifest = args.verify
    if manifest is None or not manifest.is_file():
        print(f"ERROR: manifest not found: {manifest}", file=sys.stderr)
        return 2

    try:
        ok, missing, mismatched, unexpected = _verify_manifest(
            args.root,
            manifest,
            args.algorithm,
            closed_set=bool(args.closed_set),
            exclude_globs=list(args.exclude),
            exclude_paths={args.json_report} if args.json_report is not None else set(),
        )
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: invalid manifest: {exc}", file=sys.stderr)
        return 2
    print(
        f"Verified manifest: ok={len(ok)} missing={len(missing)} "
        f"mismatched={len(mismatched)} unexpected={len(unexpected)}"
    )

    if args.json_report is not None:
        report = {
            "schema": "osqar.checksums_report.v1",
            "mode": "verify",
            "root": str(args.root.resolve()),
            "manifest": str(manifest.resolve()),
            "algorithm": str(args.algorithm),
            "closed_set": bool(args.closed_set),
            "excluded": list(args.exclude),
            "status": "PASS" if not (missing or mismatched or unexpected) else "FAIL",
            "counts": {
                "ok": len(ok),
                "missing": len(missing),
                "mismatched": len(mismatched),
                "unexpected": len(unexpected),
            },
            # Keep the report scalable: store only the problem lists by default.
            "missing": missing,
            "mismatched": mismatched,
            "unexpected": unexpected,
        }
        try:
            _write_json_report(args.json_report, report)
        except ChecksumReportError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    if missing:
        print("Missing files:")
        for p in missing:
            print(f"- {p}")

    if mismatched:
        print("Mismatched files:")
        for p in mismatched:
            print(f"- {p}")

    if unexpected:
        print("Unexpected files:")
        for p in unexpected:
            print(f"- {p}")

    return 0 if (not missing and not mismatched and not unexpected) else 1


def main() -> int:
    return cli(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
