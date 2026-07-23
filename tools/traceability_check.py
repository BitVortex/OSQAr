#!/usr/bin/env python3
"""Traceability checks for OSQAr sphinx-needs exports.

This tool consumes the ``needs.json`` (or ``needs.yaml``) produced by
sphinx-needs (via ``needs_build_json=True``) and enforces basic,
audit-friendly traceability rules.

YAML support is provided via PyYAML (optional dependency). Install with
``pip install pyyaml`` for YAML exchange format support alongside JSON.

It is intentionally dependency-free (stdlib only) for JSON mode so it can
run in CI reliably without extra packages.
"""

from __future__ import annotations

import argparse
from importlib import resources
import json
import os
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class TraceabilityReportError(RuntimeError):
    """Raised when a machine-readable report cannot be invalidated or published."""


def _invalidate_report(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        poison_exc: OSError | None = None
        try:
            with path.open("w", encoding="utf-8") as stream:
                stream.write("OSQAR INVALID STALE TRACEABILITY REPORT\n")
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as invalidation_exc:
            poison_exc = invalidation_exc
        message = f"cannot invalidate stale JSON report {path}: {exc}"
        if poison_exc is not None:
            message += f"; overwrite invalidation failed: {poison_exc}"
        raise TraceabilityReportError(message) from exc


def _write_json_report(path: Path, payload: dict[str, object]) -> None:
    temporary: Path | None = None
    descriptor: int | None = None
    stream = None
    try:
        serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        )
        temporary = Path(temporary_name)
        stream = os.fdopen(descriptor, "w", encoding="utf-8")
        descriptor = None
        stream.write(serialized)
        stream.flush()
        os.fsync(stream.fileno())
        stream.close()
        stream = None
        os.replace(temporary, path)
        temporary = None
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        cleanup_exc: OSError | None = None
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError as unlink_exc:
                cleanup_exc = unlink_exc
                marker = b"OSQAR INVALID TEMPORARY TRACEABILITY REPORT\n"
                poisoned = False
                if stream is not None:
                    try:
                        stream.seek(0)
                        stream.truncate(0)
                        stream.write(marker.decode("ascii"))
                        stream.flush()
                        os.fsync(stream.fileno())
                        poisoned = True
                    except (OSError, RuntimeError, ValueError):
                        pass
                if not poisoned:
                    poison_descriptor: int | None = None
                    try:
                        poison_descriptor = os.open(temporary, os.O_WRONLY | os.O_TRUNC)
                        os.write(poison_descriptor, marker)
                        os.fsync(poison_descriptor)
                    except OSError:
                        pass
                    finally:
                        if poison_descriptor is not None:
                            try:
                                os.close(poison_descriptor)
                            except OSError:
                                pass
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        message = f"cannot publish JSON report {path}: {exc}"
        if cleanup_exc is not None:
            message += f"; temporary cleanup failed: {cleanup_exc}"
        raise TraceabilityReportError(message) from exc


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


def _normalize_needs_list(needs_data: Any) -> list[dict[str, Any]]:
    """Normalize loaded needs data (from JSON or YAML) into a list of dicts
    with 'id' keys, regardless of sphinx-needs export format variant."""
    if isinstance(needs_data, dict):
        if "needs" in needs_data:
            if isinstance(needs_data["needs"], list):
                return [n for n in needs_data["needs"] if isinstance(n, dict)]
            # workspace-combined format: needs as dict keyed by ID
            if isinstance(needs_data["needs"], dict):
                out: list[dict[str, Any]] = []
                for need_id, need_data in needs_data["needs"].items():
                    if not isinstance(need_data, dict):
                        continue
                    if "id" not in need_data:
                        need_data = {"id": str(need_id), **need_data}
                    out.append(need_data)
                return out
        # sphinx-needs builder format: top-level has 'versions' keyed by version name.
        if "versions" in needs_data and isinstance(needs_data.get("versions"), dict):
            versions = needs_data["versions"]
            current_version = needs_data.get("current_version", "")
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
                        if "id" not in need_data:
                            need_data = {"id": str(need_id), **need_data}
                        out.append(need_data)
                    return out

    if isinstance(needs_data, list):
        return [n for n in needs_data if isinstance(n, dict)]

    raise ValueError("Unrecognized needs format")


def _load_needs(path: Path) -> list[dict[str, Any]]:
    """Load needs from a JSON or YAML file. Auto-detects format by extension.

    ``.yaml`` / ``.yml`` → YAML (requires ``pip install pyyaml``)
    ``.json`` / other → JSON (stdlib, no dependencies)
    """
    suffix = path.suffix.lower()
    raw = path.read_text(encoding="utf-8")

    if suffix in (".yaml", ".yml"):
        # --- YAML path ---
        try:
            import yaml as _yaml
        except ImportError:
            raise ImportError(
                "YAML support requires PyYAML. Install: pip install pyyaml"
            ) from None
        data = _yaml.safe_load(raw)  # type: ignore[union-attr]
        if data is None:
            raise ValueError(f"Empty YAML file: {path}")
        return _normalize_needs_list(data)

    # --- JSON path (default) ---
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: try YAML if JSON parsing fails (e.g. .json extension on YAML content)
        try:
            import yaml as _yaml
        except ImportError:
            raise ValueError(
                f"Failed to parse {path} as JSON and PyYAML is not installed. "
                f"Install with: pip install pyyaml"
            ) from None
        data = _yaml.safe_load(raw)  # type: ignore[union-attr]
        if data is None:
            raise ValueError(f"Empty file: {path}")

    return _normalize_needs_list(data)


def _collect_trace_links(need: dict[str, Any]) -> set[str]:
    linked: set[str] = set()
    for key in ("links", "links_back"):
        for link in _as_str_list(need.get(key)):
            if link:
                linked.add(link)
    return linked


def _matches_any_prefix(values: Iterable[str], prefixes: tuple[str, ...]) -> bool:
    return any(v.startswith(prefixes) for v in values)


STANDARDS_BOUNDARY = (
    "Mechanical validation only: catalog reference resolution and authored graph "
    "shape were checked; standards interpretation, applicability, adequacy, and "
    "compliance require project-authorized human review."
)


class StandardsClaimsDataError(ValueError):
    """Raised when standards input bytes cannot be decoded as declared JSON data."""


def _report_alias_label(
    report: Path, protected_inputs: list[tuple[str, Path]]
) -> str | None:
    """Return the first protected input aliased by a requested report path."""
    report_resolved = report.resolve()
    for label, protected in protected_inputs:
        if report_resolved == protected.resolve() or (
            report.exists() and protected.exists() and report.samefile(protected)
        ):
            return label
    return None


def _project_catalog_inputs(project_config: Path) -> list[tuple[str, Path]]:
    """Return file-backed catalog inputs declared by a readable project config."""
    try:
        config = json.loads(project_config.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    if not isinstance(config, dict):
        return []
    standards = config.get("standards")
    if not isinstance(standards, dict):
        return []
    declarations = standards.get("catalogs")
    if not isinstance(declarations, list):
        return []

    protected: list[tuple[str, Path]] = []
    for declaration in declarations:
        if not isinstance(declaration, dict):
            continue
        source = declaration.get("source")
        if not isinstance(source, str):
            continue
        source = source.strip()
        if (
            not source
            or source.startswith("package:")
            or ":" in source
            or Path(source).is_absolute()
        ):
            continue
        protected.append(("standards catalog", project_config.parent / source))
    return protected


def _read_catalog(source: str, project_dir: Path) -> Any:
    if source.startswith("package:"):
        package_path = source.removeprefix("package:")
        package, separator, resource = package_path.partition("/")
        if not separator or not package or not resource:
            raise ValueError(f"unsupported standards catalog source: {source}")
        raw = resources.files(package).joinpath(resource).read_text(encoding="utf-8")
    else:
        if ":" in source or Path(source).is_absolute():
            raise ValueError(f"unsupported standards catalog source: {source}")
        raw = (project_dir / source).read_text(encoding="utf-8")
    return json.loads(raw)


def _standards_meta(claim_count: int) -> dict[str, Any]:
    return {
        "counts": {
            "catalogs": 0,
            "claims": claim_count,
            "references": 0,
            "violations": 0,
        },
        "catalogs": [],
        "references": [],
        "violations": [],
        "boundary": STANDARDS_BOUNDARY,
    }


def _check_standards_claims(
    needs: list[dict[str, Any]], project_config: Path | None
) -> tuple[list[Violation], dict[str, Any]]:
    claims = [need for need in needs if str(need.get("id", "")).startswith("STDCLAIM_")]
    result = _standards_meta(len(claims))
    if not claims:
        return [], result
    if project_config is None:
        violation = Violation(
            "STANDARDS_PROJECT_CONFIG", "", "standards claims require --project-config"
        )
        result["violations"] = [violation.__dict__]
        result["counts"]["violations"] = 1
        return [violation], result

    try:
        config = json.loads(project_config.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StandardsClaimsDataError(
            f"cannot read project config {project_config}: {exc}"
        ) from exc

    catalog_refs: dict[str, set[str]] = {}
    needs_by_id = {str(need.get("id", "")): need for need in needs}
    violations: list[Violation] = []

    def add(rule: str, need_id: str, message: str) -> None:
        violations.append(Violation(rule, need_id, message))

    if not isinstance(config, dict):
        add("STANDARDS_PROJECT_CONFIG", "", "project config must be a JSON object")
        declarations: list[Any] = []
    else:
        standards = config.get("standards")
        if not isinstance(standards, dict):
            add("STANDARDS_PROJECT_CONFIG", "", "standards must be an object")
            declarations = []
        elif not isinstance(standards.get("catalogs"), list):
            add(
                "STANDARDS_PROJECT_CONFIG", "", "standards.catalogs must be a list"
            )
            declarations = []
        else:
            declarations = standards["catalogs"]

    declared_ids: set[str] = set()
    for declaration_index, declaration in enumerate(declarations):
        if not isinstance(declaration, dict):
            add(
                "STANDARDS_CATALOG_DECLARATION",
                "",
                f"catalog declaration {declaration_index} must be an object",
            )
            continue
        catalog_id_value = declaration.get("id")
        if not isinstance(catalog_id_value, str) or not catalog_id_value.strip():
            add(
                "STANDARDS_CATALOG_DECLARATION",
                "",
                f"catalog declaration {declaration_index} id must be a non-empty string",
            )
            continue
        catalog_id = catalog_id_value.strip()
        if catalog_id in declared_ids:
            violations.append(
                Violation(
                    "STANDARDS_CATALOG_DECLARATION",
                    "",
                    f"duplicate standards catalog id: {catalog_id}",
                )
            )
            continue
        declared_ids.add(catalog_id)
        source = declaration.get("source")
        if not isinstance(source, str) or not source.strip():
            add(
                "STANDARDS_CATALOG_DECLARATION",
                "",
                f"catalog {catalog_id} source must be a non-empty string",
            )
            continue
        source = source.strip()
        try:
            catalog = _read_catalog(source, project_config.parent)
        except ValueError as exc:
            add("STANDARDS_CATALOG_DECLARATION", "", str(exc))
            continue
        except (OSError, UnicodeError, ModuleNotFoundError) as exc:
            add(
                "STANDARDS_CATALOG_DECLARATION",
                "",
                f"cannot read standards catalog {catalog_id}: {exc}",
            )
            continue
        if not isinstance(catalog, dict):
            add(
                "STANDARDS_CATALOG_DECLARATION",
                "",
                f"catalog {catalog_id} must be a JSON object",
            )
            continue
        entries = catalog.get("entries")
        if not isinstance(entries, list):
            add(
                "STANDARDS_CATALOG_DECLARATION",
                "",
                f"catalog {catalog_id} entries must be a list",
            )
            continue
        reference_ids: set[str] = set()
        for entry_index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                add(
                    "STANDARDS_CATALOG_ENTRY",
                    "",
                    f"catalog {catalog_id} entry {entry_index} must be an object",
                )
                continue
            reference_value = entry.get("reference_id")
            if not isinstance(reference_value, str) or not reference_value.strip():
                add(
                    "STANDARDS_CATALOG_ENTRY",
                    "",
                    f"catalog {catalog_id} entry {entry_index} reference_id must be a non-empty string",
                )
                continue
            reference_id = reference_value.strip()
            if reference_id in reference_ids:
                add(
                    "STANDARDS_CATALOG_ENTRY",
                    "",
                    f"duplicate reference_id {reference_id} in catalog {catalog_id}",
                )
                continue
            reference_ids.add(reference_id)
        catalog_refs[catalog_id] = reference_ids

    references: list[str] = []
    for claim in claims:
        claim_id = str(claim.get("id", ""))
        catalog_value = claim.get("standards_catalog")
        catalog_id: str | None
        if not isinstance(catalog_value, str) or not catalog_value.strip():
            add(
                "STANDARDS_CLAIM",
                claim_id,
                "standards_catalog must be a non-empty string",
            )
            catalog_id = None
        else:
            catalog_id = catalog_value.strip()

        refs_value = claim.get("standards_refs")
        claim_refs: list[str] = []
        if isinstance(refs_value, str):
            if refs_value.strip():
                claim_refs = [refs_value.strip()]
            else:
                add(
                    "STANDARDS_CLAIM",
                    claim_id,
                    "standards_refs must be a non-empty string or list",
                )
        elif isinstance(refs_value, list):
            if not refs_value:
                add(
                    "STANDARDS_CLAIM",
                    claim_id,
                    "standards_refs must be a non-empty string or list",
                )
            for reference_index, reference_value in enumerate(refs_value):
                if not isinstance(reference_value, str) or not reference_value.strip():
                    add(
                        "STANDARDS_CLAIM",
                        claim_id,
                        f"standards_refs item {reference_index} must be a non-empty string",
                    )
                    continue
                reference = reference_value.strip()
                if reference in claim_refs:
                    add(
                        "STANDARDS_CLAIM",
                        claim_id,
                        f"duplicate standards_refs item after normalization: {reference}",
                    )
                    continue
                claim_refs.append(reference)
        else:
            add(
                "STANDARDS_CLAIM",
                claim_id,
                "standards_refs must be a non-empty string or list",
            )

        for field_name in ("project_interpretation", "applicability"):
            field_value = claim.get(field_name)
            if not isinstance(field_value, str) or not field_value.strip():
                add(
                    "STANDARDS_CLAIM",
                    claim_id,
                    f"{field_name} must be a non-empty string",
                )

        relation_prefixes = {
            "realized_by": ("REQ_", "LM_"),
            "verified_by": ("VER_",),
            "evidenced_by": ("EVID_",),
        }
        authored_relation_field = False
        for field_name, allowed_prefixes in relation_prefixes.items():
            if field_name not in claim:
                continue
            field_value = claim[field_name]
            # Sphinx-Needs exports configured but unauthored link fields as [].
            # Treat that representation as absent; non-empty or malformed values
            # remain authored and are validated below.
            if isinstance(field_value, list) and not field_value:
                continue
            authored_relation_field = True
            relation_targets: list[str] = []
            if isinstance(field_value, str):
                if not field_value.strip():
                    add(
                        "STANDARDS_CLAIM_RELATION",
                        claim_id,
                        f"{field_name} must be a non-empty string or list",
                    )
                else:
                    relation_targets.append(field_value.strip())
            elif isinstance(field_value, list):
                for target_index, target_value in enumerate(field_value):
                    if not isinstance(target_value, str) or not target_value.strip():
                        add(
                            "STANDARDS_CLAIM_RELATION",
                            claim_id,
                            f"{field_name} item {target_index} must be a non-empty string",
                        )
                    else:
                        target = target_value.strip()
                        if target in relation_targets:
                            add(
                                "STANDARDS_CLAIM_RELATION",
                                claim_id,
                                f"duplicate {field_name} target after normalization: {target}",
                            )
                            continue
                        relation_targets.append(target)
            else:
                add(
                    "STANDARDS_CLAIM_RELATION",
                    claim_id,
                    f"{field_name} must be a non-empty string or list",
                )
            for target in relation_targets:
                if not target.startswith(allowed_prefixes):
                    allowed = ", ".join(allowed_prefixes)
                    add(
                        "STANDARDS_CLAIM_RELATION",
                        claim_id,
                        f"{field_name} target {target} must use an allowed prefix: {allowed}",
                    )
                if target not in needs_by_id:
                    add(
                        "STANDARDS_CLAIM_RELATION",
                        claim_id,
                        f"{field_name} target does not resolve: {target}",
                    )

        if not authored_relation_field:
            add(
                "STANDARDS_CLAIM_RELATION",
                claim_id,
                "claim must author at least one relation in realized_by, verified_by, or evidenced_by",
            )

        if catalog_id is not None:
            references.extend(f"{catalog_id}:{reference}" for reference in claim_refs)
            if catalog_id not in catalog_refs:
                add(
                    "STANDARDS_REFERENCE",
                    claim_id,
                    f"unknown standards catalog: {catalog_id}",
                )
            else:
                for reference in claim_refs:
                    if reference not in catalog_refs[catalog_id]:
                        add(
                            "STANDARDS_REFERENCE",
                            claim_id,
                            f"unknown reference {catalog_id}:{reference}",
                        )

    references.sort()
    result["catalogs"] = sorted(catalog_refs)
    result["references"] = references
    result["counts"] = {
        "catalogs": len(catalog_refs),
        "claims": len(claims),
        "references": len(references),
        "violations": len(violations),
    }
    result["violations"] = [violation.__dict__ for violation in violations]
    return violations, result


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
        "--project-config",
        type=Path,
        default=None,
        help="Optional project configuration declaring standards catalogs",
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

    if args.json_report is not None:
        try:
            protected_inputs = [("needs input", args.needs_json)]
            if args.project_config is not None:
                protected_inputs.append(("project config", args.project_config))
                protected_inputs.extend(_project_catalog_inputs(args.project_config))
            alias_label = _report_alias_label(args.json_report, protected_inputs)
            if alias_label is not None:
                print(f"ERROR: JSON report aliases {alias_label}", file=sys.stderr)
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
            _invalidate_report(args.json_report)
        except (OSError, RuntimeError) as exc:
            print(f"ERROR: cannot preflight JSON report: {exc}", file=sys.stderr)
            return 2

    if not args.needs_json.is_file():
        print(f"ERROR: needs.json not found: {args.needs_json}", file=sys.stderr)
        return 2

    try:
        needs = _load_needs(args.needs_json)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Failed to read {args.needs_json}: {exc}", file=sys.stderr)
        return 2

    if not needs:
        print(f"ERROR: no needs found in {args.needs_json}", file=sys.stderr)
        return 2

    seen_ids: set[str] = set()
    for need in needs:
        need_id = str(need.get("id", "")).strip()
        if not need_id:
            print("ERROR: need is missing a non-empty id", file=sys.stderr)
            return 2
        if need_id in seen_ids:
            print(f"ERROR: duplicate need id: {need_id}", file=sys.stderr)
            return 2
        seen_ids.add(need_id)

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

    try:
        standards_violations, standards_meta = _check_standards_claims(
            needs, args.project_config
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Failed to validate standards claims: {exc}", file=sys.stderr)
        return 2
    violations.extend(standards_violations)
    meta["counts"]["violations_total"] = len(violations)

    if args.json_report is not None:
        report = {
            "meta": meta,
            "standards_claims": standards_meta,
            "violations": [v.__dict__ for v in violations],
        }
        try:
            _write_json_report(args.json_report, report)
        except TraceabilityReportError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

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
