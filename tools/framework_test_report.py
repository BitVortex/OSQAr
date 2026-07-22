"""Fail-closed validation of OSQAr's framework JUnit evidence."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from tools.junit_evidence import JUnitEvidenceError, read_junit_report


class FrameworkReportError(ValueError):
    """Raised when framework test evidence is absent or unacceptable."""


def _invalidate_json_report(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        raise FrameworkReportError(f"cannot invalidate JSON report: {exc}") from exc


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
        raise FrameworkReportError(message) from exc


def validate_junit_report(path: Path) -> dict[str, int]:
    if not path.is_file():
        raise FrameworkReportError(f"JUnit report not found: {path}")
    try:
        counts = read_junit_report(path)
    except (OSError, ET.ParseError) as exc:
        raise FrameworkReportError(f"malformed JUnit report: {exc}") from exc
    except JUnitEvidenceError as exc:
        raise FrameworkReportError(str(exc)) from exc
    if counts["failures"] or counts["errors"]:
        raise FrameworkReportError(
            f"framework tests failed: failures={counts['failures']} errors={counts['errors']}"
        )
    if counts["skipped"]:
        raise FrameworkReportError(
            f"required framework tests were skipped: {counts['skipped']}"
        )
    return counts


def cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate framework JUnit evidence")
    parser.add_argument("report", type=Path)
    parser.add_argument("--json-report", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.json_report is not None:
        try:
            collision = args.report.resolve() == args.json_report.resolve()
        except (OSError, RuntimeError) as exc:
            print(f"ERROR: cannot resolve report paths: {exc}", file=sys.stderr)
            return 2
        if collision:
            print(
                "ERROR: JUnit input and JSON output resolve to the same path",
                file=sys.stderr,
            )
            return 2
        try:
            _invalidate_json_report(args.json_report)
        except FrameworkReportError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
    try:
        counts = validate_junit_report(args.report)
    except FrameworkReportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    payload = {"schema": "osqar.framework-test-report.v1", "status": "PASS", **counts}
    if args.json_report is not None:
        try:
            _write_json_report(args.json_report, payload)
        except FrameworkReportError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
    print(
        f"Framework test report: PASS ({counts['tests']} tests, "
        f"{counts['skipped']} skipped)"
    )
    return 0


def main() -> int:
    return cli(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
