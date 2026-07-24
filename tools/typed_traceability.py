"""Directed, typed traceability validation and API allocation projections."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.osqar_evidence import validate_project

REPORT_SCHEMA = "osqar.traceability-report.v1"
REPORT_SCHEMA_VERSION = 1
PROFILE_VERSION = 1
API_SCHEMA = "osqar.api-requirements.v1"
API_AUDIT_SCHEMA = "osqar.api-requirements-audit.v1"
DEFAULT_API_PREFIXES = ("API_", "IMPL_")
ACTIVE_PARTICIPATING_TYPES = {
    "requirement",
    "architecture",
    "implementation",
    "verification",
}

TYPE_ALIASES = {
    "req": "requirement",
    "need": "requirement",
    "arch": "architecture",
    "ver": "verification",
    "test": "verification",
    "impl": "implementation",
    "api": "implementation",
    "code": "implementation",
    "result": "result",
    "evidence": "evidence",
    "lm": "lifecycle",
    "sc": "safety-case",
}
PREFIX_TYPES = (
    ("REQ_", "requirement"),
    ("ARCH_", "architecture"),
    ("VER_", "verification"),
    ("TEST_", "verification"),
    ("RESULT_", "result"),
    ("EVID_", "evidence"),
    ("API_", "implementation"),
    ("IMPL_", "implementation"),
    ("CODE_", "implementation"),
    ("LM_", "lifecycle"),
    ("SC_", "safety-case"),
)
KNOWN_TYPES = {
    "requirement",
    "architecture",
    "implementation",
    "verification",
    "result",
    "evidence",
    "lifecycle",
    "safety-case",
}
ALLOWED_KINDS = {
    "implementation": {"", "api", "code", "component"},
    "lifecycle": {"assumption", "baseline", "configuration", "gap", "deviation"},
    "safety-case": {"claim", "strategy", "context", "assumption", "evidence-reference"},
}


@dataclass(frozen=True)
class RelationRule:
    name: str
    source_types: tuple[str, ...]
    target_types: tuple[str, ...]
    minimum: int
    maximum: int | None = None
    source_kind: str | None = None
    target_minimum: int = 0
    target_maximum: int | None = None


RULES = (
    RelationRule("allocated_to", ("requirement",), ("architecture",), 1, target_minimum=1),
    RelationRule("allocated_to_api", ("requirement",), ("implementation",), 0),
    RelationRule("realized_by", ("architecture",), ("implementation",), 1),
    RelationRule("verified_by", ("requirement",), ("verification",), 1, target_minimum=1),
    RelationRule(
        "produces",
        ("verification",),
        ("result",),
        1,
        target_minimum=1,
        target_maximum=1,
    ),
    RelationRule("evidenced_by", ("result",), ("evidence",), 1, target_minimum=1),
    RelationRule(
        "supported_by",
        ("safety-case",),
        ("safety-case", "result", "evidence"),
        1,
        source_kind="claim",
    ),
    RelationRule(
        "references",
        ("safety-case",),
        ("result", "evidence"),
        1,
        source_kind="evidence-reference",
    ),
    RelationRule(
        "constrains",
        ("lifecycle",),
        ("requirement", "architecture", "verification"),
        1,
        source_kind="assumption",
    ),
    RelationRule(
        "applies_to",
        ("lifecycle",),
        ("requirement", "verification", "result", "evidence"),
        1,
        source_kind="deviation",
    ),
)
RULES_BY_NAME = {rule.name: rule for rule in RULES}


@dataclass(frozen=True)
class TraceabilityReport:
    profile: str
    schema: str
    status: str
    executed_rules: tuple[str, ...]
    violations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "schema_version": REPORT_SCHEMA_VERSION,
            "profile": self.profile,
            "profile_version": PROFILE_VERSION,
            "status": self.status,
            "executed_rules": list(self.executed_rules),
            "violations": list(self.violations),
            "claim": (
                "qualification-profile typed traceability passed"
                if self.profile == "qualification" and self.status == "PASS"
                else "basic compatibility validation completed"
                if self.profile == "basic" and self.status == "PASS"
                else "typed traceability did not pass"
            ),
            "limitations": [
                "graph validation does not establish semantic adequacy, compliance, qualification, certification, or safety"
            ],
        }


def _need_id(need: dict[str, Any]) -> str:
    return str(need.get("id") or "").strip()


def _need_type(need: dict[str, Any]) -> str:
    declared = str(need.get("type") or "").strip().lower()
    normalized = TYPE_ALIASES.get(declared, declared)
    if normalized in KNOWN_TYPES:
        return normalized
    need_id = _need_id(need)
    for prefix, entity_type in PREFIX_TYPES:
        if need_id.startswith(prefix):
            return entity_type
    return normalized or "unknown"


def _title(need: dict[str, Any]) -> str:
    value = str(need.get("title") or need.get("content") or _need_id(need))
    return " ".join(value.split())


def _relations(need: dict[str, Any], violations: list[str]) -> dict[str, list[str]]:
    need_id = _need_id(need) or "<missing-id>"
    raw = need.get("relations", {})
    if not isinstance(raw, dict):
        violations.append(f"{need_id}: relations must be an object")
        raw = {}
    merged = dict(raw)
    for relation_name in RULES_BY_NAME:
        if relation_name in need and relation_name not in merged:
            merged[relation_name] = need[relation_name]
    normalized: dict[str, list[str]] = {}
    for name, targets in merged.items():
        relation_name = str(name)
        if relation_name not in RULES_BY_NAME:
            violations.append(f"{need_id}: unknown relation {relation_name}")
            continue
        if not isinstance(targets, list) or any(not isinstance(target, str) for target in targets):
            violations.append(f"{need_id}: relation {relation_name} targets must be a list of IDs")
            continue
        target_ids = [target.strip() for target in targets if target.strip()]
        if len(target_ids) != len(set(target_ids)):
            violations.append(f"{need_id}: relation {relation_name} contains duplicate targets")
        normalized[relation_name] = list(dict.fromkeys(target_ids))
    return normalized


def _rule_applies(rule: RelationRule, entity_type: str, kind: str) -> bool:
    return entity_type in rule.source_types and (
        rule.source_kind is None or kind == rule.source_kind
    )


def _accepted_evidence_target(
    need_id: str,
    needs_by_id: dict[str, dict[str, Any]],
    *,
    accepted_activity_ids: frozenset[str],
    visiting: frozenset[str] = frozenset(),
) -> bool:
    """Resolve accepted support to independent result/evidence leaves.

    A safety-case node cannot establish its own acceptance merely through a
    status field. Its authored support chain must be non-empty, acyclic, and
    terminate only in accepted result/evidence nodes.
    """

    if need_id in visiting:
        return False
    need = needs_by_id.get(need_id)
    if need is None:
        return False
    entity_type = _need_type(need)
    if entity_type == "result":
        return (
            need.get("acceptance_activity") in accepted_activity_ids
            and need.get("status") in {"passed", "passed-with-deviation"}
            and need.get("evidence_state") == "approved"
        )
    if entity_type == "evidence":
        return (
            need.get("acceptance_activity") in accepted_activity_ids
            and need.get("evidence_state") == "approved"
            and need.get("status") != "superseded"
        )
    if entity_type != "safety-case" or need.get("status") not in {"supported", "accepted"}:
        return False

    relations = _relations(need, [])
    targets = relations.get("supported_by", []) + relations.get("references", [])
    if not targets:
        return False
    next_visiting = visiting | {need_id}
    return all(
        _accepted_evidence_target(
            target_id,
            needs_by_id,
            accepted_activity_ids=accepted_activity_ids,
            visiting=next_visiting,
        )
        for target_id in targets
    )


def validate_typed_traceability(
    needs: list[dict[str, Any]],
    *,
    profile: str,
    evidence_project: Path | None = None,
    expected_source_revision: str | None = None,
    expected_configuration_sha256: str | None = None,
) -> TraceabilityReport:
    if profile != "qualification":
        return TraceabilityReport(
            profile=profile,
            schema=REPORT_SCHEMA,
            status="PASS",
            executed_rules=(),
            violations=(),
        )

    violations: list[str] = []
    accepted_activity_ids: frozenset[str] = frozenset()
    if evidence_project is None:
        violations.append(
            "qualification requires authoritative framework acceptance from tools.osqar_evidence"
        )
    else:
        framework_result = validate_project(
            evidence_project,
            profile_name="qualification",
            expected_source_revision=expected_source_revision,
            expected_configuration_sha256=expected_configuration_sha256,
        )
        if framework_result.status != "PASS" or not framework_result.acceptance_claimed:
            violations.extend(
                f"framework acceptance failed: {failure}"
                for failure in framework_result.failures
            )
            if not framework_result.failures:
                violations.append("framework acceptance failed without an acceptance claim")
        else:
            accepted_activity_ids = frozenset(
                str(activity.get("id"))
                for activity in framework_result.activities
                if isinstance(activity, dict) and activity.get("id")
            )
    needs_by_id: dict[str, dict[str, Any]] = {}
    for index, need in enumerate(needs):
        if not isinstance(need, dict):
            violations.append(f"need {index}: must be an object")
            continue
        need_id = _need_id(need)
        if not need_id:
            violations.append(f"need {index}: missing id")
            continue
        if need_id in needs_by_id:
            violations.append(f"duplicate need id: {need_id}")
            continue
        needs_by_id[need_id] = need

    relation_cache: dict[str, dict[str, list[str]]] = {}
    for need_id, need in sorted(needs_by_id.items()):
        entity_type = _need_type(need)
        kind = str(need.get("kind") or "")
        if entity_type not in KNOWN_TYPES:
            violations.append(f"{need_id}: unknown entity type {entity_type!r}")
        allowed_kinds = ALLOWED_KINDS.get(entity_type)
        if allowed_kinds is not None and kind not in allowed_kinds:
            violations.append(f"{need_id}: unsupported {entity_type} kind {kind!r}")
        if (
            entity_type in ACTIVE_PARTICIPATING_TYPES
            and str(need.get("status") or "") != "active"
        ):
            violations.append(
                f"{need_id}: participating node status {need.get('status')!r}; expected 'active'"
            )
        relations = _relations(need, violations)
        relation_cache[need_id] = relations

        for relation_name in relations:
            rule = RULES_BY_NAME[relation_name]
            if not _rule_applies(rule, entity_type, kind):
                violations.append(
                    f"{need_id}: relation {relation_name} is not allowed for type {entity_type}"
                )

        for rule in RULES:
            if not _rule_applies(rule, entity_type, kind):
                continue
            targets = relations.get(rule.name, [])
            if len(targets) < rule.minimum:
                violations.append(
                    f"{need_id}: relation {rule.name} requires at least {rule.minimum} target(s)"
                )
            if rule.maximum is not None and len(targets) > rule.maximum:
                violations.append(
                    f"{need_id}: relation {rule.name} allows at most {rule.maximum} target(s)"
                )
            for target_id in targets:
                target = needs_by_id.get(target_id)
                if target is None:
                    violations.append(
                        f"{need_id}: relation {rule.name} target {target_id} does not exist"
                    )
                    continue
                target_type = _need_type(target)
                if target_type not in rule.target_types:
                    violations.append(
                        f"{need_id}: relation {rule.name} target {target_id} has type {target_type}; "
                        f"expected {', '.join(rule.target_types)}"
                    )
                if (
                    rule.name == "evidenced_by"
                    and need.get("acceptance_activity")
                    != target.get("acceptance_activity")
                ):
                    violations.append(
                        f"{need_id}: evidenced_by target {target_id} binds activity "
                        f"{target.get('acceptance_activity')!r}; expected "
                        f"{need.get('acceptance_activity')!r}"
                    )
                if rule.name in {"supported_by", "references"} and not _accepted_evidence_target(
                    target_id,
                    needs_by_id,
                    accepted_activity_ids=accepted_activity_ids,
                ):
                    violations.append(f"{need_id}: target {target_id} is not accepted evidence")

        if entity_type in {"result", "evidence"}:
            activity_id = need.get("acceptance_activity")
            if not isinstance(activity_id, str) or not activity_id:
                violations.append(f"{need_id}: acceptance_activity is required")
            elif activity_id not in accepted_activity_ids:
                violations.append(
                    f"{need_id}: acceptance activity {activity_id!r} was not accepted"
                )
            if not _accepted_evidence_target(
                need_id,
                needs_by_id,
                accepted_activity_ids=accepted_activity_ids,
            ):
                violations.append(f"{need_id}: {entity_type} is not accepted")

    graph = {
        source_id: tuple(
            target_id
            for targets in relation_cache[source_id].values()
            for target_id in targets
            if target_id in needs_by_id
        )
        for source_id in sorted(needs_by_id)
    }
    visited: set[str] = set()
    active: list[str] = []
    active_set: set[str] = set()
    reported_cycles: set[tuple[str, ...]] = set()

    def visit(need_id: str) -> None:
        if need_id in visited:
            return
        if need_id in active_set:
            start = active.index(need_id)
            cycle = tuple(active[start:] + [need_id])
            if cycle not in reported_cycles:
                reported_cycles.add(cycle)
                violations.append(f"traceability cycle: {' -> '.join(cycle)}")
            return
        active.append(need_id)
        active_set.add(need_id)
        for target_id in graph[need_id]:
            visit(target_id)
        active.pop()
        active_set.remove(need_id)
        visited.add(need_id)

    for need_id in graph:
        visit(need_id)

    for rule in RULES:
        if rule.target_minimum == 0 and rule.target_maximum is None:
            continue
        incoming_counts: dict[str, int] = {need_id: 0 for need_id in needs_by_id}
        for source_id, relations in relation_cache.items():
            source = needs_by_id[source_id]
            if not _rule_applies(
                rule, _need_type(source), str(source.get("kind") or "")
            ):
                continue
            for target_id in relations.get(rule.name, []):
                if target_id in incoming_counts:
                    incoming_counts[target_id] += 1
        for target_id, target in sorted(needs_by_id.items()):
            if _need_type(target) not in rule.target_types:
                continue
            count = incoming_counts[target_id]
            if count < rule.target_minimum:
                violations.append(
                    f"{target_id}: relation {rule.name} requires at least "
                    f"{rule.target_minimum} incoming source(s)"
                )
            if rule.target_maximum is not None and count > rule.target_maximum:
                violations.append(
                    f"{target_id}: relation {rule.name} allows at most "
                    f"{rule.target_maximum} incoming source(s)"
                )

    executed = tuple(
        f"{rule.source_types[0]}.{rule.name}"
        + (f"[{rule.source_kind}]" if rule.source_kind else "")
        for rule in RULES
    )
    return TraceabilityReport(
        profile=profile,
        schema=REPORT_SCHEMA,
        status="FAIL" if violations else "PASS",
        executed_rules=executed,
        violations=tuple(violations),
    )


def _is_api(
    need: dict[str, Any], *, api_prefixes: tuple[str, ...] = DEFAULT_API_PREFIXES
) -> bool:
    need_id = _need_id(need)
    return _need_type(need) == "implementation" and (
        str(need.get("kind") or "") == "api"
        or any(need_id.startswith(prefix) for prefix in api_prefixes)
    )


def _project_api_requirement_paths_unchecked(
    needs: list[dict[str, Any]],
    *,
    profile: str,
    api_prefixes: tuple[str, ...] = DEFAULT_API_PREFIXES,
) -> list[dict[str, Any]]:
    """Return deterministic paths after the qualification boundary was checked."""
    needs_by_id = {
        _need_id(need): need
        for need in needs
        if isinstance(need, dict) and _need_id(need)
    }
    api_ids = sorted(
        need_id
        for need_id, need in needs_by_id.items()
        if _is_api(need, api_prefixes=api_prefixes)
    )
    paths: list[dict[str, Any]] = []
    allocated_apis: set[str] = set()

    for requirement_id, requirement in sorted(needs_by_id.items()):
        if _need_type(requirement) != "requirement":
            continue
        relations = _relations(requirement, [])
        for api_id in sorted(relations.get("allocated_to_api", [])):
            if api_id not in api_ids:
                continue
            allocated_apis.add(api_id)
            paths.append(
                {
                    "schema": API_AUDIT_SCHEMA,
                    "profile": profile,
                    "api_id": api_id,
                    "requirement_id": requirement_id,
                    "path": [requirement_id, api_id],
                    "relations": ["allocated_to_api"],
                    "allocation_status": "allocated",
                }
            )
        for architecture_id in sorted(relations.get("allocated_to", [])):
            architecture = needs_by_id.get(architecture_id)
            if architecture is None or _need_type(architecture) != "architecture":
                continue
            architecture_relations = _relations(architecture, [])
            for api_id in sorted(architecture_relations.get("realized_by", [])):
                if api_id not in api_ids:
                    continue
                allocated_apis.add(api_id)
                paths.append(
                    {
                        "schema": API_AUDIT_SCHEMA,
                        "profile": profile,
                        "api_id": api_id,
                        "requirement_id": requirement_id,
                        "path": [requirement_id, architecture_id, api_id],
                        "relations": ["allocated_to", "realized_by"],
                        "allocation_status": "allocated",
                    }
                )

    for api_id in api_ids:
        if api_id not in allocated_apis:
            paths.append(
                {
                    "schema": API_AUDIT_SCHEMA,
                    "profile": profile,
                    "api_id": api_id,
                    "requirement_id": None,
                    "path": [api_id],
                    "relations": [],
                    "allocation_status": "unallocated",
                }
            )
    return sorted(
        paths,
        key=lambda item: (
            str(item["api_id"]),
            str(item["requirement_id"] or ""),
            tuple(item["path"]),
        ),
    )


def project_api_requirement_paths(
    needs: list[dict[str, Any]],
    *,
    profile: str,
    evidence_project: Path | None = None,
    expected_source_revision: str | None = None,
    expected_configuration_sha256: str | None = None,
    api_prefixes: tuple[str, ...] = DEFAULT_API_PREFIXES,
) -> list[dict[str, Any]]:
    """Validate and return deterministic, audit-preserving allocation paths."""

    if profile != "qualification":
        raise ValueError("API allocation artifacts require profile 'qualification'")
    report = validate_typed_traceability(
        needs,
        profile=profile,
        evidence_project=evidence_project,
        expected_source_revision=expected_source_revision,
        expected_configuration_sha256=expected_configuration_sha256,
    )
    if report.status != "PASS":
        raise ValueError(
            "typed traceability validation failed: " + "; ".join(report.violations)
        )
    return _project_api_requirement_paths_unchecked(
        needs, profile=profile, api_prefixes=api_prefixes
    )


def project_api_requirements(
    needs: list[dict[str, Any]],
    *,
    profile: str,
    evidence_project: Path | None = None,
    expected_source_revision: str | None = None,
    expected_configuration_sha256: str | None = None,
    api_prefixes: tuple[str, ...] = DEFAULT_API_PREFIXES,
) -> list[dict[str, str]]:
    needs_by_id = {
        _need_id(need): need
        for need in needs
        if isinstance(need, dict) and _need_id(need)
    }
    requirements_by_api: dict[str, set[str]] = {
        need_id: set()
        for need_id, need in needs_by_id.items()
        if _is_api(need, api_prefixes=api_prefixes)
    }
    for path in project_api_requirement_paths(
        needs,
        profile=profile,
        evidence_project=evidence_project,
        expected_source_revision=expected_source_revision,
        expected_configuration_sha256=expected_configuration_sha256,
        api_prefixes=api_prefixes,
    ):
        requirement_id = path["requirement_id"]
        if isinstance(requirement_id, str):
            requirements_by_api[path["api_id"]].add(requirement_id)

    rows: list[dict[str, str]] = []
    for api_id in sorted(requirements_by_api):
        api = needs_by_id[api_id]
        requirement_ids = sorted(requirements_by_api[api_id])
        rows.append(
            {
                "API_ID": api_id,
                "API_Title": _title(api),
                "Requirement_IDs": ";".join(requirement_ids),
                "Requirement_Titles": ";".join(
                    _title(needs_by_id[item]) for item in requirement_ids
                ),
                "Allocation_Status": "allocated" if requirement_ids else "unallocated",
                "Profile": profile,
                "Schema": API_SCHEMA,
            }
        )
    return rows
