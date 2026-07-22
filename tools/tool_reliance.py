"""Validation for the versioned OSQAr tool-reliance boundary."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "osqar.tool-reliance.v1"
DESIGNATED_REVIEWER = "BitVortex"
_REQUIRED_FUNCTION_FIELDS = {
    "id",
    "command",
    "boundary",
    "reliance_permitted",
    "tool_impact",
    "tool_error_detection",
    "tool_confidence_level",
    "erroneous_output",
    "independent_detection",
    "evidence",
    "human_judgment",
    "owner",
    "input",
    "output",
    "exclusions",
    "lifecycle_decision",
    "assumptions",
    "operating_constraints",
    "profile_applicability",
    "environment_applicability",
    "configuration",
    "dependencies",
    "known_anomalies",
    "anomaly_disposition",
    "residual_limitations",
    "revalidation_triggers",
    "review",
}
_ALLOWED_BOUNDARIES = {"candidate", "convenience", "excluded"}


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_non_empty(item) for item in value)


def _exact_version(value: Any) -> bool:
    return _non_empty(value) and re.fullmatch(
        r"v?\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?", value.strip()
    ) is not None


def _exact_profile_version(value: Any) -> bool:
    return _non_empty(value) and re.fullmatch(r"\d+(?:\.\d+)*", value.strip()) is not None


def _immutable_evidence(value: Any, evidence_root: Path | None) -> bool:
    if not isinstance(value, list) or not value or evidence_root is None:
        return False
    root = evidence_root.expanduser().resolve()
    for item in value:
        if not isinstance(item, dict):
            return False
        if not all(
            _non_empty(item.get(field))
            for field in ("id", "uri", "revision", "sha256", "artifact")
        ):
            return False
        digest = item["sha256"].strip().lower()
        revision = item["revision"].strip().lower()
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            return False
        if len(revision) not in {40, 64} or any(
            character not in "0123456789abcdef" for character in revision
        ):
            return False
        if item["uri"].strip().lower() != f"urn:sha256:{digest}":
            return False
        if not item["id"].strip().lower().endswith(f"@{revision}"):
            return False
        relative = Path(item["artifact"])
        if relative.is_absolute():
            return False
        artifact = (root / relative).resolve()
        try:
            artifact.relative_to(root)
            content = artifact.read_bytes()
            envelope = json.loads(content)
        except (OSError, ValueError, json.JSONDecodeError):
            return False
        if hashlib.sha256(content).hexdigest() != digest:
            return False
        if not isinstance(envelope, dict) or envelope.get("schema") != "osqar.validation-evidence.v1":
            return False
        if str(envelope.get("revision") or "").strip().lower() != revision:
            return False
    return True


def _resolved_string(value: Any) -> bool:
    return _non_empty(value) and value.strip().lower() not in {
        "unresolved",
        "unknown",
        "latest",
        "none",
        "tbd",
        "*",
    }


def _resolved_string_list(value: Any) -> bool:
    return _non_empty_string_list(value) and all(_resolved_string(item) for item in value)


def _resolved_lifecycle_decision(value: Any) -> bool:
    return isinstance(value, dict) and all(
        _resolved_string(value.get(field))
        for field in ("id", "description", "owner", "work_product")
    )


def _immutable_configuration(value: Any) -> bool:
    if not isinstance(value, dict) or not _resolved_string(value.get("identifier")):
        return False
    digest = str(value.get("sha256") or "").strip().lower()
    return len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)


def _exact_dependencies(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, dict)
        and _resolved_string(item.get("name"))
        and _resolved_string(item.get("version"))
        for item in value
    )


def _reviewed_anomaly_disposition(value: Any) -> bool:
    if not isinstance(value, dict) or value.get("status") not in {"none-known", "reviewed"}:
        return False
    revision = str(value.get("review_revision") or "").strip().lower()
    return len(revision) in {40, 64} and all(
        character in "0123456789abcdef" for character in revision
    )


def _controlled_anomaly_register(
    value: Any, *, function_id: str, osqar_version: str
) -> bool:
    required = {
        "affected_functions",
        "versions",
        "impact",
        "workaround",
        "detection_status",
        "prior_outputs_require_regeneration",
    }
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, dict)
        and required <= set(item)
        and _resolved_string_list(item.get("affected_functions"))
        and function_id in item["affected_functions"]
        and _resolved_string_list(item.get("versions"))
        and osqar_version in item["versions"]
        and all(
            _resolved_string(item.get(field))
            for field in ("impact", "workaround", "detection_status")
        )
        and isinstance(item.get("prior_outputs_require_regeneration"), bool)
        for item in value
    )


def validate_tool_reliance_inventory(
    payload: Any, *, evidence_root: Path | None = None
) -> list[str]:
    """Return all structural and fail-closed reliance-policy violations."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["tool-reliance inventory must be an object"]
    if payload.get("schema") != SCHEMA:
        errors.append(f"unsupported schema: {payload.get('schema')!r}")

    applicability = payload.get("version_applicability")
    if not isinstance(applicability, dict):
        errors.append("version_applicability must be an object")
        applicability = {}
    if applicability.get("status") not in {"unresolved", "reviewed"}:
        errors.append("version_applicability status must be unresolved or reviewed")
    if not _non_empty(applicability.get("osqar_version")):
        errors.append("version_applicability requires osqar_version")

    standards = payload.get("standards_basis")
    if not isinstance(standards, dict):
        errors.append("standards_basis must be an object")
    else:
        if standards.get("reference") != "ISO 26262-8:2018 Clause 11":
            errors.append("standards_basis must identify ISO 26262-8:2018 Clause 11")
        if standards.get("interpretation_status") not in {
            "researched-pending-controlled-review",
            "controlled-copy-reviewed",
        }:
            errors.append("standards interpretation status is missing or unsupported")
    if not _non_empty(payload.get("claim_boundary")):
        errors.append("claim_boundary is required")

    functions = payload.get("functions")
    if not isinstance(functions, list) or not functions:
        errors.append("functions must be a non-empty list")
        return errors

    seen: set[str] = set()
    for index, item in enumerate(functions):
        if not isinstance(item, dict):
            errors.append(f"function {index} must be an object")
            continue
        missing = sorted(_REQUIRED_FUNCTION_FIELDS - set(item))
        if missing:
            errors.append(f"function {index} missing fields: {', '.join(missing)}")
        function_id = str(item.get("id") or "").strip()
        if not function_id:
            errors.append(f"function {index} has no id")
        elif function_id in seen:
            errors.append(f"duplicate function id: {function_id}")
        seen.add(function_id)
        if item.get("boundary") not in _ALLOWED_BOUNDARIES:
            errors.append(f"{function_id}: unsupported boundary")
        if not isinstance(item.get("reliance_permitted"), bool):
            errors.append(f"{function_id}: reliance_permitted must be boolean")
        for field in (
            "command",
            "tool_impact",
            "tool_error_detection",
            "tool_confidence_level",
            "erroneous_output",
            "human_judgment",
            "owner",
        ):
            if not _non_empty(item.get(field)):
                errors.append(f"{function_id}: {field} is required")
        for field in ("independent_detection", "evidence"):
            if not isinstance(item.get(field), list):
                errors.append(f"{function_id}: {field} must be a list")
        for field in (
            "input",
            "output",
            "exclusions",
            "assumptions",
            "operating_constraints",
            "profile_applicability",
            "environment_applicability",
            "dependencies",
            "known_anomalies",
            "residual_limitations",
            "revalidation_triggers",
        ):
            if not isinstance(item.get(field), list):
                errors.append(f"{function_id}: {field} must be a list")
        if not isinstance(item.get("configuration"), dict):
            errors.append(f"{function_id}: configuration must be an object")
        if not isinstance(item.get("lifecycle_decision"), dict):
            errors.append(f"{function_id}: lifecycle_decision must be an object")
        if not isinstance(item.get("anomaly_disposition"), dict):
            errors.append(f"{function_id}: anomaly_disposition must be an object")
        review = item.get("review")
        if not isinstance(review, dict) or not _non_empty(review.get("reviewer")):
            errors.append(f"{function_id}: review must identify a reviewer")
            review = {}
        if review.get("status") not in {"pending", "approved", "rejected"}:
            errors.append(f"{function_id}: invalid review status")

        if item.get("reliance_permitted") is True:
            for field in (
                "tool_impact",
                "tool_error_detection",
                "tool_confidence_level",
                "erroneous_output",
                "human_judgment",
                "owner",
            ):
                if not _resolved_string(item.get(field)):
                    errors.append(f"{function_id}: reliance requires resolved {field}")
            for field in ("input", "output", "exclusions"):
                if not _resolved_string_list(item.get(field)):
                    errors.append(f"{function_id}: reliance requires resolved {field}")
            if applicability.get("status") != "reviewed" or not _exact_version(
                applicability.get("osqar_version")
            ):
                errors.append(f"{function_id}: reliance requires an exact OSQAr version")
            if not _exact_profile_version(applicability.get("qualification_profile_version")):
                errors.append(
                    f"{function_id}: reliance requires an exact qualification profile version"
                )
            if not _resolved_string_list(applicability.get("supported_environments")):
                errors.append(f"{function_id}: reliance requires a resolved supported environment")
            if not _exact_version(applicability.get("python_version")):
                errors.append(f"{function_id}: reliance requires an exact Python version")
            dependency_revision = str(
                applicability.get("dependency_set_revision") or ""
            ).strip().lower()
            if len(dependency_revision) != 64 or any(
                character not in "0123456789abcdef" for character in dependency_revision
            ):
                errors.append(
                    f"{function_id}: reliance requires an immutable dependency-set revision"
                )
            if not isinstance(standards, dict) or standards.get(
                "interpretation_status"
            ) != "controlled-copy-reviewed":
                errors.append(
                    f"{function_id}: reliance requires controlled-copy-reviewed standards basis"
                )
            if not _resolved_string_list(item.get("independent_detection")):
                errors.append(
                    f"{function_id}: reliance requires non-empty independent detection entries"
                )
            if not _immutable_evidence(item.get("evidence"), evidence_root):
                errors.append(
                    f"{function_id}: reliance requires immutable evidence and versioned evidence identifiers"
                )
            if not _resolved_lifecycle_decision(item.get("lifecycle_decision")):
                errors.append(f"{function_id}: reliance requires a resolved lifecycle decision")
            if not _resolved_string_list(item.get("profile_applicability")):
                errors.append(f"{function_id}: reliance requires resolved profile applicability")
            if not _resolved_string_list(item.get("environment_applicability")):
                errors.append(
                    f"{function_id}: reliance requires resolved environment applicability"
                )
            if not _immutable_configuration(item.get("configuration")):
                errors.append(f"{function_id}: reliance requires immutable configuration")
            if not _exact_dependencies(item.get("dependencies")):
                errors.append(f"{function_id}: reliance requires exact dependencies")
            if not _controlled_anomaly_register(
                item.get("known_anomalies"),
                function_id=function_id,
                osqar_version=str(applicability.get("osqar_version") or "").strip(),
            ):
                errors.append(f"{function_id}: reliance requires a controlled known-anomaly register")
            if not _reviewed_anomaly_disposition(item.get("anomaly_disposition")):
                errors.append(f"{function_id}: reliance requires reviewed anomaly disposition")
            for field in (
                "assumptions",
                "operating_constraints",
                "residual_limitations",
                "revalidation_triggers",
            ):
                if not _resolved_string_list(item.get(field)):
                    errors.append(f"{function_id}: reliance requires resolved {field}")
            if (
                not isinstance(standards, dict)
                or standards.get("reviewer") != DESIGNATED_REVIEWER
                or review.get("reviewer") != DESIGNATED_REVIEWER
                or review.get("status") != "approved"
            ):
                errors.append(
                    f"{function_id}: reliance requires independent approval by the designated reviewer"
                )
            if item.get("boundary") != "candidate":
                errors.append(f"{function_id}: only reviewed candidate functions may be relied upon")
    return errors
