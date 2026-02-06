#!/usr/bin/env python3
"""Traceability checks for OSQAr sphinx-needs exports.

This tool consumes the `needs.json` produced by sphinx-needs (via `needs_build_json=True`)
and enforces basic, audit-friendly traceability rules.

It is intentionally dependency-free (stdlib only) so it can run in CI reliably.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Violation:
    rule: str
    need_id: str
    message: str


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v is not None]
    if isinstance(value, str):
        return [value]
    return [str(value)]


def _load_needs(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, dict):
        if "needs" in data and isinstance(data["needs"], list):
            return [n for n in data["needs"] if isinstance(n, dict)]
        # sphinx-needs builder format: top-level has 'versions' keyed by version name.
        if "versions" in data and isinstance(data.get("versions"), dict):
            versions = data["versions"]
            current_version = data.get("current_version", "")
            if current_version in versions and isinstance(
                versions[current_version], dict
            ):
                needs = versions[current_version].get("needs")
                if isinstance(needs, list):
                    return [n for n in needs if isinstance(n, dict)]
                if isinstance(needs, dict):
                    out: list[dict[str, Any]] = []
                    for need_id, need_data in needs.items():
                        if not isinstance(need_data, dict):
                            continue
                        # Some formats store the id only as the dict key.
                        if "id" not in need_data:
                            need_data = {"id": str(need_id), **need_data}
                        out.append(need_data)
                    return out

    if isinstance(data, list):
        return [n for n in data if isinstance(n, dict)]

    raise ValueError("Unrecognized needs.json format")


def _collect_trace_links(need: dict[str, Any]) -> set[str]:
    linked: set[str] = set()
    for key in ("links", "links_back"):
        for link in _as_str_list(need.get(key)):
            if link:
                linked.add(link)
    return linked


def _matches_any_prefix(values: Iterable[str], prefixes: tuple[str, ...]) -> bool:
    return any(v.startswith(prefixes) for v in values)


def _run_checks(
    needs: list[dict[str, Any]],
    *,
    req_prefixes: tuple[str, ...],
    arch_prefixes: tuple[str, ...],
    test_prefixes: tuple[str, ...],
    code_prefixes: tuple[str, ...],
    enforce_req_traces_arch: bool,
    enforce_req_has_test: bool,
    enforce_arch_traces_req: bool,
    enforce_test_traces_req: bool,
    enforce_no_dead_links: bool,
) -> tuple[list[Violation], dict[str, Any]]:
    needs_by_id: dict[str, dict[str, Any]] = {}
    for need in needs:
        need_id = str(need.get("id", ""))
        if need_id:
            needs_by_id[need_id] = need

    violations: list[Violation] = []

    # Rule (default): Requirements should trace to architecture.
    if enforce_req_traces_arch:
        for need_id, need in needs_by_id.items():
            if not need_id.startswith(req_prefixes):
                continue
            links = _collect_trace_links(need)
            if not _matches_any_prefix(links, arch_prefixes):
                violations.append(
                    Violation(
                        rule="REQ_TRACES_ARCH",
                        need_id=need_id,
                        message=(
                            f"Requirement {need_id} has no trace link to any architecture item (prefixes: {arch_prefixes}). "
                            "Add a link either from REQ_* to ARCH_*, or from ARCH_* back to REQ_*."
                        ),
                    )
                )

    # Rule (optional): Requirements must trace to at least one test.
    if enforce_req_has_test:
        for need_id, need in needs_by_id.items():
            if not need_id.startswith(req_prefixes):
                continue
            links = _collect_trace_links(need)
            if not _matches_any_prefix(links, test_prefixes):
                violations.append(
                    Violation(
                        rule="REQ_HAS_TEST",
                        need_id=need_id,
                        message=(
                            f"Requirement {need_id} has no trace link to any test (prefixes: {test_prefixes}). "
                            "Add a link either from the requirement to a TEST_* need, or from a TEST_* need back to it."
                        ),
                    )
                )

    # Rule (optional): Architecture items should trace to requirements.
    if enforce_arch_traces_req:
        for need_id, need in needs_by_id.items():
            if not need_id.startswith(arch_prefixes):
                continue
            links = _collect_trace_links(need)
            if not _matches_any_prefix(links, req_prefixes):
                violations.append(
                    Violation(
                        rule="ARCH_TRACES_REQ",
                        need_id=need_id,
                        message=(
                            f"Architecture item {need_id} has no trace link to any requirement (prefixes: {req_prefixes}). "
                            "Add a link either from ARCH_* to REQ_*, or from REQ_* to ARCH_*."
                        ),
                    )
                )

    # Rule (optional): Tests should trace to requirements.
    if enforce_test_traces_req:
        for need_id, need in needs_by_id.items():
            if not need_id.startswith(test_prefixes):
                continue
            links = _collect_trace_links(need)
            if not _matches_any_prefix(links, req_prefixes):
                violations.append(
                    Violation(
                        rule="TEST_TRACES_REQ",
                        need_id=need_id,
                        message=(
                            f"Test {need_id} has no trace link to any requirement (prefixes: {req_prefixes}). "
                            "Add a link either from TEST_* to REQ_*, or from REQ_* to TEST_*."
                        ),
                    )
                )

    # Rule (default): Outgoing links must resolve to existing needs.
    if enforce_no_dead_links:
        for need_id, need in needs_by_id.items():
            outgoing = _as_str_list(need.get("links"))
            for target in outgoing:
                if not target:
                    continue
                if target not in needs_by_id:
                    violations.append(
                        Violation(
                            rule="NO_DEAD_LINKS",
                            need_id=need_id,
                            message=f"Need {need_id} has outgoing link to unknown need id: {target}",
                        )
                    )

    meta = {
        "counts": {
            "needs_total": len(needs_by_id),
            "req_total": sum(1 for k in needs_by_id if k.startswith(req_prefixes)),
            "arch_total": sum(1 for k in needs_by_id if k.startswith(arch_prefixes)),
            "test_total": sum(1 for k in needs_by_id if k.startswith(test_prefixes)),
            "code_total": sum(1 for k in needs_by_id if k.startswith(code_prefixes)),
            "violations_total": len(violations),
        },
        "prefixes": {
            "requirements": list(req_prefixes),
            "architecture": list(arch_prefixes),
            "tests": list(test_prefixes),
            "code": list(code_prefixes),
        },
    }

    return violations, meta


def cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Validate traceability rules from a sphinx-needs needs.json export"
    )
    parser.add_argument(
        "needs_json", type=Path, help="Path to needs.json produced by sphinx-needs"
    )
    parser.add_argument(
        "--json-report",
        type=Path,
        default=None,
        help="Optional path to write a machine-readable JSON report",
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
        help="Implementation/code ID prefix (repeatable). Default: CODE_, IMPL_",
    )

    parser.add_argument(
        "--enforce-req-traces-arch",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fail if any REQ_* has no ARCH_* trace link (default: true)",
    )
    parser.add_argument(
        "--enforce-req-has-test",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Fail if any REQ_* has no TEST_* trace link (default: false)",
    )
    parser.add_argument(
        "--enforce-arch-traces-req",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Fail if any ARCH_* has no REQ_* trace link (default: false)",
    )
    parser.add_argument(
        "--enforce-test-traces-req",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Fail if any TEST_* has no REQ_* trace link (default: false)",
    )
    parser.add_argument(
        "--enforce-no-dead-links",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fail if any outgoing link points to a missing need id (default: true)",
    )

    args = parser.parse_args(argv)

    if not args.needs_json.is_file():
        print(f"ERROR: needs.json not found: {args.needs_json}", file=sys.stderr)
        return 2

    try:
        needs = _load_needs(args.needs_json)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Failed to read {args.needs_json}: {exc}", file=sys.stderr)
        return 2

    violations, meta = _run_checks(
        needs,
        req_prefixes=tuple(args.req_prefix),
        arch_prefixes=tuple(args.arch_prefix),
        test_prefixes=tuple(args.test_prefix),
        code_prefixes=tuple(args.code_prefix),
        enforce_req_traces_arch=bool(args.enforce_req_traces_arch),
        enforce_req_has_test=bool(args.enforce_req_has_test),
        enforce_arch_traces_req=bool(args.enforce_arch_traces_req),
        enforce_test_traces_req=bool(args.enforce_test_traces_req),
        enforce_no_dead_links=bool(args.enforce_no_dead_links),
    )

    if args.json_report is not None:
        report = {
            "meta": meta,
            "violations": [v.__dict__ for v in violations],
        }
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    counts = meta["counts"]
    print(
        "Traceability check summary: "
        f"needs={counts['needs_total']} req={counts['req_total']} arch={counts['arch_total']} "
        f"test={counts['test_total']} violations={counts['violations_total']}"
    )

    if not violations:
        return 0

    print("Violations:")
    for v in violations:
        print(f"- {v.rule}: {v.need_id}: {v.message}")

    return 1


def main() -> int:
    return cli(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
