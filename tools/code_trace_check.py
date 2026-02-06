#!/usr/bin/env python3
"""Code/implementation traceability checks for OSQAr.

This tool scans implementation and test source trees for OSQAr need IDs such as:
- REQ_* (requirements)
- ARCH_* (architecture)
- TEST_* (verification)

It optionally compares IDs found in code to IDs defined in a sphinx-needs
`needs.json` export and can enforce simple, CI-friendly rules like:
- every REQ_/ARCH_ must appear at least once in implementation sources
- every TEST_ must appear at least once in test sources

Design goals:
- dependency-free (stdlib only)
- robust across languages by treating files as text
- safe defaults (reporting by default; enforcement is opt-in)
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_needs_ids(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))

    def normalize_ids(needs: Any) -> list[str]:
        out: list[str] = []
        if isinstance(needs, list):
            for n in needs:
                if isinstance(n, dict) and n.get("id"):
                    out.append(str(n["id"]))
        elif isinstance(needs, dict):
            for need_id, need_data in needs.items():
                if isinstance(need_data, dict) and need_data.get("id"):
                    out.append(str(need_data["id"]))
                else:
                    out.append(str(need_id))
        return out

    if isinstance(data, dict):
        if isinstance(data.get("needs"), list):
            return normalize_ids(data["needs"])

        # sphinx-needs builder format: top-level has 'versions' keyed by version name.
        if isinstance(data.get("versions"), dict):
            versions = data["versions"]
            current_version = str(data.get("current_version") or "")
            chosen_version = current_version if current_version in versions else None
            if chosen_version is None:
                # Fall back to the first version key (stable order).
                keys = sorted(str(k) for k in versions.keys())
                chosen_version = keys[0] if keys else None

            if (
                chosen_version is not None
                and chosen_version in versions
                and isinstance(versions[chosen_version], dict)
            ):
                v = versions[chosen_version]
                if "needs" in v:
                    return normalize_ids(v.get("needs"))

    if isinstance(data, list):
        return normalize_ids(data)

    raise ValueError("Unrecognized needs.json format")


def _compile_id_regex(prefixes: tuple[str, ...]) -> re.Pattern[str]:
    # Match IDs embedded in code/comments without matching within longer tokens.
    # Example: REQ_FUNC_001, TEST_THRESHOLD_001
    if not prefixes:
        return re.compile(r"a^")
    parts = "|".join(re.escape(p) for p in sorted(prefixes, key=len, reverse=True))
    return re.compile(rf"(?<![A-Z0-9_])(?:{parts})[A-Z0-9_]+(?![A-Z0-9_])")


def _posix_rel(root: Path, p: Path) -> str:
    return p.resolve().relative_to(root.resolve()).as_posix()


def _iter_text_files(
    root: Path,
    scan_roots: list[Path],
    *,
    exts: set[str],
    exclude_globs: list[str],
    max_bytes: int,
) -> list[Path]:
    root = root.resolve()

    def is_excluded(rel: str) -> bool:
        return any(fnmatch.fnmatch(rel, g) for g in exclude_globs)

    files: list[Path] = []
    for sr in scan_roots:
        sr = sr.resolve()
        if not sr.exists():
            continue

        if sr.is_file():
            candidate = sr
            rel = _posix_rel(root, candidate)
            if (not exts or candidate.suffix in exts) and not is_excluded(rel):
                try:
                    if candidate.stat().st_size <= max_bytes:
                        files.append(candidate)
                except OSError:
                    pass
            continue

        for p in sr.rglob("*"):
            if not p.is_file():
                continue
            rel = _posix_rel(root, p)
            if is_excluded(rel):
                continue
            if exts and p.suffix not in exts:
                continue
            try:
                if p.stat().st_size > max_bytes:
                    continue
            except OSError:
                continue
            files.append(p)

    return sorted(set(files), key=lambda x: _posix_rel(root, x))


def _scan_files_for_ids(
    root: Path,
    files: list[Path],
    *,
    id_re: re.Pattern[str],
) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, int]]]:
    """Return (by_id, by_file).

    - by_id[id][file] = count
    - by_file[file][id] = count
    """
    root = root.resolve()
    by_id: dict[str, dict[str, int]] = {}
    by_file: dict[str, dict[str, int]] = {}

    for p in files:
        rel = _posix_rel(root, p)
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        matches = id_re.findall(text)
        if not matches:
            continue

        counts: dict[str, int] = {}
        for mid in matches:
            counts[mid] = counts.get(mid, 0) + 1

        by_file[rel] = dict(sorted(counts.items()))
        for mid, cnt in counts.items():
            by_id.setdefault(mid, {})[rel] = cnt

    return by_id, by_file


def _starts_with_any(value: str, prefixes: tuple[str, ...]) -> bool:
    return value.startswith(prefixes) if prefixes else False


def _pick_default_scan_roots(root: Path) -> tuple[list[Path], list[Path]]:
    root = root.resolve()

    impl_candidates = ["src", "include", "lib"]
    test_candidates = ["tests", "test"]

    impl = [root / d for d in impl_candidates if (root / d).exists()]
    tests = [root / d for d in test_candidates if (root / d).exists()]

    if not impl and not tests:
        impl = [root]

    return impl, tests


def cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scan implementation/test source trees for OSQAr need IDs (REQ_/ARCH_/TEST_...) "
            "and optionally enforce coverage against a needs.json export."
        )
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Project root directory to scan (default: .)",
    )
    parser.add_argument(
        "--needs-json",
        type=Path,
        default=None,
        help="Optional needs.json to derive the expected REQ_/ARCH_/TEST_ IDs",
    )
    parser.add_argument(
        "--json-report",
        type=Path,
        default=None,
        help="Optional path to write a machine-readable JSON report",
    )

    parser.add_argument(
        "--impl-dir",
        action="append",
        default=[],
        help=(
            "Implementation directory/file relative to --root (repeatable). "
            "Default: auto-detect (src/include/lib)"
        ),
    )
    parser.add_argument(
        "--test-dir",
        action="append",
        default=[],
        help=(
            "Test directory/file relative to --root (repeatable). "
            "Default: auto-detect (tests/test)"
        ),
    )

    parser.add_argument(
        "--req-prefix",
        action="append",
        default=["REQ_"],
        help="Requirement ID prefix (repeatable). Default: REQ_",
    )
    parser.add_argument(
        "--arch-prefix",
        action="append",
        default=["ARCH_"],
        help="Architecture ID prefix (repeatable). Default: ARCH_",
    )
    parser.add_argument(
        "--test-prefix",
        action="append",
        default=["TEST_"],
        help="Test ID prefix (repeatable). Default: TEST_",
    )
    parser.add_argument(
        "--code-prefix",
        action="append",
        default=["CODE_", "IMPL_"],
        help="Implementation/code ID prefix to recognize (repeatable). Default: CODE_, IMPL_",
    )

    parser.add_argument(
        "--ext",
        action="append",
        default=[],
        help=(
            "File extension to scan, including leading dot (repeatable). "
            "Default: a broad set of common source/doc extensions"
        ),
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude glob(s) relative to --root (repeatable), e.g. '**/_build/**'",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=2_000_000,
        help="Skip files larger than this many bytes (default: 2000000)",
    )

    parser.add_argument(
        "--enforce-req-in-impl",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Fail if any REQ_* from needs.json is not found in implementation sources (default: false)",
    )
    parser.add_argument(
        "--enforce-arch-in-impl",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Fail if any ARCH_* from needs.json is not found in implementation sources (default: false)",
    )
    parser.add_argument(
        "--enforce-test-in-tests",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Fail if any TEST_* from needs.json is not found in test sources (default: false)",
    )
    parser.add_argument(
        "--enforce-no-unknown-ids",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Fail if code mentions IDs that are not present in needs.json (default: false)",
    )

    args = parser.parse_args(argv)

    root: Path = args.root.expanduser().resolve()
    if not root.exists():
        print(f"ERROR: root not found: {root}", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"ERROR: root is not a directory: {root}", file=sys.stderr)
        return 2

    needs_json: Optional[Path] = (
        args.needs_json.expanduser().resolve() if args.needs_json else None
    )
    if needs_json is not None and not needs_json.is_file():
        print(f"ERROR: needs.json not found: {needs_json}", file=sys.stderr)
        return 2

    enforcement_requested = bool(
        args.enforce_req_in_impl
        or args.enforce_arch_in_impl
        or args.enforce_test_in_tests
        or args.enforce_no_unknown_ids
    )
    if enforcement_requested and needs_json is None:
        print(
            "ERROR: enforcement requires --needs-json (to define expected IDs)",
            file=sys.stderr,
        )
        return 2

    req_prefixes = tuple(args.req_prefix)
    arch_prefixes = tuple(args.arch_prefix)
    test_prefixes = tuple(args.test_prefix)
    code_prefixes = tuple(args.code_prefix)
    prefixes_all = req_prefixes + arch_prefixes + test_prefixes + code_prefixes

    id_re = _compile_id_regex(prefixes_all)

    default_exts = {
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".cc",
        ".cxx",
        ".rs",
        ".py",
        ".ts",
        ".js",
        ".java",
        ".kt",
        ".cs",
        ".go",
        ".sh",
        ".ps1",
        ".cmd",
        ".bat",
        ".md",
        ".rst",
        ".txt",
        ".yml",
        ".yaml",
        ".toml",
        ".ini",
        ".cfg",
        ".json",
        ".xml",
    }
    exts = (
        {e if e.startswith(".") else f".{e}" for e in (args.ext or [])}
        if (args.ext or [])
        else default_exts
    )

    exclude_globs = list(args.exclude or [])

    if args.impl_dir or args.test_dir:
        impl_roots = [root / d for d in args.impl_dir]
        test_roots = [root / d for d in args.test_dir]
        if not impl_roots and not test_roots:
            impl_roots, test_roots = _pick_default_scan_roots(root)
    else:
        impl_roots, test_roots = _pick_default_scan_roots(root)

    impl_files = _iter_text_files(
        root,
        impl_roots,
        exts=exts,
        exclude_globs=exclude_globs,
        max_bytes=int(args.max_bytes),
    )
    test_files = _iter_text_files(
        root,
        test_roots,
        exts=exts,
        exclude_globs=exclude_globs,
        max_bytes=int(args.max_bytes),
    )

    impl_by_id, impl_by_file = _scan_files_for_ids(root, impl_files, id_re=id_re)
    test_by_id, test_by_file = _scan_files_for_ids(root, test_files, id_re=id_re)

    expected_ids: list[str] = []
    if needs_json is not None:
        try:
            expected_ids = _load_needs_ids(needs_json)
        except Exception as exc:  # noqa: BLE001
            print(
                f"ERROR: failed to parse needs.json: {needs_json} ({exc})",
                file=sys.stderr,
            )
            return 2

    expected_req = sorted(
        {i for i in expected_ids if _starts_with_any(i, req_prefixes)}
    )
    expected_arch = sorted(
        {i for i in expected_ids if _starts_with_any(i, arch_prefixes)}
    )
    expected_test = sorted(
        {i for i in expected_ids if _starts_with_any(i, test_prefixes)}
    )
    expected_set = set(expected_ids)

    impl_found_ids = set(impl_by_id.keys())
    test_found_ids = set(test_by_id.keys())

    missing_req_in_impl = [i for i in expected_req if i not in impl_found_ids]
    missing_arch_in_impl = [i for i in expected_arch if i not in impl_found_ids]
    missing_test_in_tests = [i for i in expected_test if i not in test_found_ids]

    unknown_ids: list[str] = []
    if needs_json is not None:
        unknown_ids = sorted((impl_found_ids | test_found_ids) - expected_set)

    violations: list[str] = []
    if args.enforce_req_in_impl and missing_req_in_impl:
        violations.append(f"REQ_IN_IMPL missing={len(missing_req_in_impl)}")
    if args.enforce_arch_in_impl and missing_arch_in_impl:
        violations.append(f"ARCH_IN_IMPL missing={len(missing_arch_in_impl)}")
    if args.enforce_test_in_tests and missing_test_in_tests:
        violations.append(f"TEST_IN_TESTS missing={len(missing_test_in_tests)}")
    if args.enforce_no_unknown_ids and unknown_ids:
        violations.append(f"UNKNOWN_IDS count={len(unknown_ids)}")

    report: dict[str, Any] = {
        "schema": "osqar.code_trace_report.v1",
        "generated_at": _utc_now_iso(),
        "root": str(root),
        "inputs": {
            "needs_json": str(needs_json) if needs_json else None,
            "impl_roots": [str(p) for p in impl_roots],
            "test_roots": [str(p) for p in test_roots],
            "exclude": exclude_globs,
            "ext": sorted(exts),
            "max_bytes": int(args.max_bytes),
            "prefixes": {
                "requirements": list(req_prefixes),
                "architecture": list(arch_prefixes),
                "tests": list(test_prefixes),
                "code": list(code_prefixes),
            },
            "enforcement": {
                "enforce_req_in_impl": bool(args.enforce_req_in_impl),
                "enforce_arch_in_impl": bool(args.enforce_arch_in_impl),
                "enforce_test_in_tests": bool(args.enforce_test_in_tests),
                "enforce_no_unknown_ids": bool(args.enforce_no_unknown_ids),
            },
        },
        "counts": {
            "impl_files_scanned": len(impl_files),
            "test_files_scanned": len(test_files),
            "impl_ids_found": len(impl_by_id),
            "test_ids_found": len(test_by_id),
            "expected_req": len(expected_req),
            "expected_arch": len(expected_arch),
            "expected_test": len(expected_test),
            "missing_req_in_impl": len(missing_req_in_impl),
            "missing_arch_in_impl": len(missing_arch_in_impl),
            "missing_test_in_tests": len(missing_test_in_tests),
            "unknown_ids": len(unknown_ids),
            "violations": len(violations),
        },
        "expected": {
            "req": expected_req,
            "arch": expected_arch,
            "test": expected_test,
        },
        "missing": {
            "req_in_impl": missing_req_in_impl,
            "arch_in_impl": missing_arch_in_impl,
            "test_in_tests": missing_test_in_tests,
        },
        "unknown_ids": unknown_ids,
        "found": {
            "impl": {
                "by_id": {
                    k: dict(sorted(v.items())) for k, v in sorted(impl_by_id.items())
                },
                "by_file": {
                    k: dict(sorted(v.items())) for k, v in sorted(impl_by_file.items())
                },
            },
            "tests": {
                "by_id": {
                    k: dict(sorted(v.items())) for k, v in sorted(test_by_id.items())
                },
                "by_file": {
                    k: dict(sorted(v.items())) for k, v in sorted(test_by_file.items())
                },
            },
        },
        "ok": not violations,
        "violations": violations,
    }

    print(
        "Code trace summary: "
        f"impl_files={report['counts']['impl_files_scanned']} "
        f"test_files={report['counts']['test_files_scanned']} "
        f"expected(req/arch/test)={report['counts']['expected_req']}/{report['counts']['expected_arch']}/{report['counts']['expected_test']} "
        f"missing(req/arch/test)={report['counts']['missing_req_in_impl']}/{report['counts']['missing_arch_in_impl']}/{report['counts']['missing_test_in_tests']} "
        f"unknown_ids={report['counts']['unknown_ids']} "
        f"violations={report['counts']['violations']}"
    )

    if args.json_report is not None:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    if violations:
        if args.enforce_req_in_impl and missing_req_in_impl:
            print(f"Missing REQ_* in implementation: {len(missing_req_in_impl)}")
        if args.enforce_arch_in_impl and missing_arch_in_impl:
            print(f"Missing ARCH_* in implementation: {len(missing_arch_in_impl)}")
        if args.enforce_test_in_tests and missing_test_in_tests:
            print(f"Missing TEST_* in tests: {len(missing_test_in_tests)}")
        if args.enforce_no_unknown_ids and unknown_ids:
            print(f"Unknown IDs referenced in code: {len(unknown_ids)}")
        return 1

    return 0


def main() -> int:
    return cli(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
