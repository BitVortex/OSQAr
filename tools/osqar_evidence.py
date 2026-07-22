"""Evidence state and acceptance validation for OSQAr projects.

The validator establishes mechanical acceptance only. It does not judge whether
requirements, evidence, or a safety argument are semantically adequate.
"""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.junit_evidence import JUnitEvidenceError, validate_junit_tree

ALLOWED_RESULT_STATES = {
    "not-run",
    "invalid",
    "failed",
    "passed",
    "passed-with-deviation",
}
ACCEPTED_RESULT_STATES = {"passed", "passed-with-deviation"}
ALLOWED_GAP_STATES = {"open", "approved", "closed"}
ALLOWED_ACTIVITY_STATES = {"planned", "ready", "running", "completed", "failed", "waived"}
ALLOWED_EVIDENCE_STATES = {"missing", "generated", "validated", "approved", "superseded"}
ALLOWED_ACTIVITY_TRANSITIONS = {
    "planned": {"ready", "waived"},
    "ready": {"running", "waived"},
    "running": {"completed", "failed"},
    "failed": {"ready", "waived"},
    "completed": set(),
    "waived": set(),
}


@dataclass(frozen=True)
class ValidationResult:
    profile: str
    status: str
    acceptance_claimed: bool
    activities: tuple[dict[str, Any], ...]
    failures: tuple[str, ...]
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "osqar.acceptance-report.v1",
            "profile": self.profile,
            "status": self.status,
            "acceptance_claimed": self.acceptance_claimed,
            "activities": list(self.activities),
            "failures": list(self.failures),
            "limitations": list(self.limitations),
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _junit_rejection(path: Path) -> str | None:
    tree = ET.parse(path)
    try:
        totals = validate_junit_tree(tree.getroot())
    except JUnitEvidenceError as exc:
        return str(exc)
    if totals["failures"] or totals["errors"] or totals["skipped"]:
        return (
            f"tests={totals['tests']}, failures={totals['failures']}, "
            f"errors={totals['errors']}, skipped={totals['skipped']}"
        )
    return None


def _project_report_path(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    relative = Path(value)
    if relative.is_absolute():
        return None
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    return path


def _validate_activity(
    activity: Any,
    *,
    root: Path,
    index: int,
    source_revision: str,
    configuration_id: str,
    configuration_sha256: str,
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    if not isinstance(activity, dict):
        return {"index": index}, [f"verification.run[{index}] must be an object"]

    activity_id = str(activity.get("id") or "").strip()
    required_value = activity.get("required", True)
    if not isinstance(required_value, bool):
        failures.append(f"activity {activity_id or index}: required must be a boolean")
        required = True
    else:
        required = required_value
    status = str(activity.get("status") or "not-run").strip()
    activity_state = str(activity.get("activity_state") or "planned").strip()
    evidence_state = str(activity.get("evidence_state") or "missing").strip()
    summary: dict[str, Any] = {
        "id": activity_id,
        "required": required,
        "activity_state": activity_state,
        "status": status,
        "evidence_state": evidence_state,
    }

    if not activity_id:
        failures.append(f"verification.run[{index}] has no id")
    if status not in ALLOWED_RESULT_STATES:
        failures.append(f"activity {activity_id or index}: unknown result status {status!r}")
    if required and status not in ACCEPTED_RESULT_STATES:
        failures.append(f"activity {activity_id or index}: required activity is not accepted ({status})")
    if activity_state not in ALLOWED_ACTIVITY_STATES:
        failures.append(f"activity {activity_id or index}: unknown activity state {activity_state!r}")
    elif required and activity_state != "completed":
        failures.append(f"activity {activity_id or index}: required activity is not completed")
    if evidence_state not in ALLOWED_EVIDENCE_STATES:
        failures.append(f"activity {activity_id or index}: unknown evidence state {evidence_state!r}")
    elif required and evidence_state != "approved":
        failures.append(f"activity {activity_id or index}: evidence is not approved ({evidence_state})")
    if str(activity.get("applicability") or "") != "applicable":
        failures.append(f"activity {activity_id or index}: applicability must be explicit and applicable")

    history = activity.get("activity_history", [activity_state])
    if not isinstance(history, list) or not history:
        failures.append(f"activity {activity_id or index}: activity_history must be a non-empty list")
    else:
        normalized_history = [str(item) for item in history]
        if normalized_history[0] != "planned":
            failures.append(
                f"activity {activity_id or index}: activity_history must begin with planned"
            )
        unknown_states = [
            state for state in normalized_history if state not in ALLOWED_ACTIVITY_STATES
        ]
        if unknown_states:
            failures.append(
                f"activity {activity_id or index}: activity_history contains unknown states: "
                + ", ".join(repr(state) for state in unknown_states)
            )
        if normalized_history[-1] != activity_state:
            failures.append(f"activity {activity_id or index}: activity_history does not end in current state")
        for previous, current in zip(normalized_history, normalized_history[1:]):
            if current not in ALLOWED_ACTIVITY_TRANSITIONS.get(previous, set()):
                failures.append(
                    f"activity {activity_id or index}: prohibited activity transition {previous} -> {current}"
                )

    for field in (
        "command",
        "source_revision",
        "configuration_id",
        "configuration_sha256",
    ):
        if not isinstance(activity.get(field), str) or not str(activity[field]).strip():
            failures.append(f"activity {activity_id or index}: missing provenance field {field}")
    if str(activity.get("source_revision") or "").strip() != source_revision:
        failures.append(
            f"activity {activity_id or index}: source_revision does not match project source_revision"
        )
    if str(activity.get("configuration_id") or "").strip() != configuration_id:
        failures.append(
            f"activity {activity_id or index}: configuration_id does not match project configuration_id"
        )
    if str(activity.get("configuration_sha256") or "").strip().lower() != configuration_sha256:
        failures.append(
            f"activity {activity_id or index}: configuration_sha256 does not match project configuration_sha256"
        )

    tool = activity.get("tool")
    if not isinstance(tool, dict) or not str(tool.get("name") or "").strip() or not str(
        tool.get("version") or ""
    ).strip():
        failures.append(f"activity {activity_id or index}: tool name and version are required")
    elif tool.get("available") is not True:
        failures.append(f"activity {activity_id or index}: required tool is unavailable")
    environment = activity.get("environment")
    if not isinstance(environment, dict) or not environment:
        failures.append(f"activity {activity_id or index}: non-empty environment provenance is required")

    report = _project_report_path(root, activity.get("report"))
    if report is None:
        failures.append(f"activity {activity_id or index}: report must be a project-relative path")
    elif not report.is_file():
        failures.append(f"activity {activity_id or index}: report does not exist: {activity.get('report')}")
    elif report.stat().st_size == 0:
        failures.append(f"activity {activity_id or index}: report is empty: {activity.get('report')}")
    else:
        expected_hash = str(activity.get("report_sha256") or "").strip().lower()
        try:
            actual_hash = _sha256(report)
        except OSError as exc:
            failures.append(
                f"activity {activity_id or index}: failed to read report: {exc}"
            )
            actual_hash = ""
        summary["report"] = str(activity.get("report"))
        if actual_hash:
            summary["report_sha256"] = actual_hash
        if len(expected_hash) != 64 or any(c not in "0123456789abcdef" for c in expected_hash):
            failures.append(f"activity {activity_id or index}: valid report_sha256 is required")
        elif not actual_hash:
            pass
        elif actual_hash != expected_hash:
            failures.append(f"activity {activity_id or index}: report_sha256 does not match report bytes")

        report_format = str(activity.get("report_format") or "")
        if required and report_format != "junit-xml":
            failures.append(
                f"activity {activity_id or index}: required qualification activity requires a machine-interpretable report format"
            )
        if report_format == "junit-xml":
            try:
                rejection = _junit_rejection(report)
                if rejection is not None:
                    failures.append(
                        f"activity {activity_id or index}: junit-xml report is not accepted: {rejection}"
                    )
            except (ET.ParseError, OSError) as exc:
                failures.append(
                    f"activity {activity_id or index}: malformed junit-xml report: {exc}"
                )
        elif report_format != "opaque":
            failures.append(
                f"activity {activity_id or index}: unsupported report_format {report_format!r}"
            )

    if status == "passed-with-deviation":
        deviation = activity.get("deviation")
        if (
            not isinstance(deviation, dict)
            or deviation.get("status") != "approved"
            or not str(deviation.get("reviewer") or "").strip()
            or not str(deviation.get("rationale") or "").strip()
        ):
            failures.append(
                f"activity {activity_id or index}: passed-with-deviation requires an approved deviation with reviewer and rationale"
            )

    findings = activity.get("findings")
    if not isinstance(findings, list):
        failures.append(f"activity {activity_id or index}: findings must be a list")
    else:
        for finding_index, finding in enumerate(findings):
            if not isinstance(finding, dict):
                failures.append(f"activity {activity_id or index}: finding {finding_index} must be an object")
                continue
            finding_id = str(finding.get("id") or finding_index)
            finding_status = str(finding.get("status") or "open")
            if finding_status not in {"closed", "approved-deviation"}:
                failures.append(
                    f"activity {activity_id or index}: finding {finding_id} is undispositioned ({finding_status})"
                )
            elif finding_status == "approved-deviation" and (
                not str(finding.get("reviewer") or "").strip()
                or not str(finding.get("rationale") or "").strip()
            ):
                failures.append(
                    f"activity {activity_id or index}: finding {finding_id} deviation lacks reviewer or rationale"
                )

    thresholds = activity.get("thresholds")
    if not isinstance(thresholds, list):
        failures.append(f"activity {activity_id or index}: thresholds must be a list")
    else:
        comparators = {
            ">=": lambda observed, target: observed >= target,
            ">": lambda observed, target: observed > target,
            "<=": lambda observed, target: observed <= target,
            "<": lambda observed, target: observed < target,
            "==": lambda observed, target: observed == target,
        }
        for threshold_index, threshold in enumerate(thresholds):
            if not isinstance(threshold, dict):
                failures.append(
                    f"activity {activity_id or index}: threshold {threshold_index} must be an object"
                )
                continue
            metric = str(threshold.get("metric") or threshold_index)
            operator = str(threshold.get("operator") or "")
            observed = threshold.get("observed")
            target = threshold.get("target")
            comparator = comparators.get(operator)
            if comparator is None or not isinstance(observed, (int, float)) or not isinstance(
                target, (int, float)
            ):
                failures.append(
                    f"activity {activity_id or index}: threshold {metric} is malformed"
                )
            elif not comparator(observed, target):
                failures.append(
                    f"activity {activity_id or index}: threshold failed for {metric}: "
                    f"{observed} {operator} {target}"
                )

    return summary, failures


def _validate_gaps(gaps: Any) -> list[str]:
    failures: list[str] = []
    if gaps is None:
        return failures
    if not isinstance(gaps, dict):
        return ["verification.gaps must be an object"]
    for gap_id, gap in sorted(gaps.items()):
        if not isinstance(gap, dict):
            failures.append(f"gap {gap_id}: definition must be an object")
            continue
        status = str(gap.get("status") or "open")
        if status not in ALLOWED_GAP_STATES:
            failures.append(f"gap {gap_id}: unknown gap status {status!r}")
            continue
        required = gap.get("required", True)
        if not isinstance(required, bool):
            failures.append(f"gap {gap_id}: required must be a boolean")
            required = True
        if required and status == "open":
            failures.append(f"gap {gap_id}: required gap remains open")
        if status == "approved" and (
            not str(gap.get("reviewer") or "").strip()
            or not str(gap.get("rationale") or "").strip()
        ):
            failures.append(f"gap {gap_id}: approved gap requires reviewer and rationale")
    return failures


def validate_project(
    project_path: Path,
    *,
    profile_name: str | None = None,
    expected_source_revision: str | None = None,
    expected_configuration_sha256: str | None = None,
) -> ValidationResult:
    project_path = project_path.expanduser().resolve()
    try:
        data = json.loads(project_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return ValidationResult(
            profile=profile_name or "unknown",
            status="FAIL",
            acceptance_claimed=False,
            activities=(),
            failures=(f"failed to load project configuration: {exc}",),
            limitations=(),
        )
    if not isinstance(data, dict):
        return ValidationResult(
            profile=profile_name or "unknown",
            status="FAIL",
            acceptance_claimed=False,
            activities=(),
            failures=("project configuration must be a JSON object",),
            limitations=(),
        )

    configured_profile = str(data.get("profile") or "basic")
    profile = profile_name or configured_profile
    if profile not in {"basic", "qualification"}:
        return ValidationResult(
            profile=profile,
            status="FAIL",
            acceptance_claimed=False,
            activities=(),
            failures=(f"unknown profile: {profile}",),
            limitations=(),
        )
    if configured_profile != profile:
        return ValidationResult(
            profile=profile,
            status="FAIL",
            acceptance_claimed=False,
            activities=(),
            failures=(
                f"requested profile {profile!r} does not match project profile {configured_profile!r}",
            ),
            limitations=(),
        )

    if profile == "basic":
        return ValidationResult(
            profile=profile,
            status="PASS",
            acceptance_claimed=False,
            activities=(),
            failures=(),
            limitations=(
                "basic profile does not establish qualification evidence acceptance",
                "listed-file integrity and documentation traceability remain separate checks",
            ),
        )

    verification = data.get("verification")
    if not isinstance(verification, dict):
        verification = {}
    source_revision_value = data.get("source_revision")
    source_revision = (
        source_revision_value.strip().lower()
        if isinstance(source_revision_value, str)
        else ""
    )
    configuration_id_value = data.get("configuration_id")
    configuration_id = (
        configuration_id_value.strip()
        if isinstance(configuration_id_value, str)
        else ""
    )
    configuration_sha256_value = data.get("configuration_sha256")
    configuration_sha256 = (
        configuration_sha256_value.strip().lower()
        if isinstance(configuration_sha256_value, str)
        else ""
    )
    trusted_source = str(expected_source_revision or "").strip().lower()
    trusted_configuration = str(expected_configuration_sha256 or "").strip().lower()
    run = verification.get("run")
    failures: list[str] = []
    if len(source_revision) not in {40, 64} or any(
        character not in "0123456789abcdef" for character in source_revision
    ):
        failures.append("qualification profile requires a 40- or 64-hex project source_revision")
    if not trusted_source:
        failures.append("qualification profile requires trusted expected_source_revision")
    elif source_revision != trusted_source:
        failures.append(
            "project source_revision does not match trusted expected_source_revision"
        )
    if not configuration_id:
        failures.append("qualification profile requires project configuration_id")
    if len(configuration_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in configuration_sha256
    ):
        failures.append("qualification profile requires valid project configuration_sha256")
    if not trusted_configuration:
        failures.append("qualification profile requires trusted expected_configuration_sha256")
    elif configuration_sha256 != trusted_configuration:
        failures.append(
            "project configuration_sha256 does not match trusted expected_configuration_sha256"
        )
    activities: list[dict[str, Any]] = []
    if not isinstance(run, list) or not run:
        failures.append("qualification profile requires at least one verification activity")
        run = []

    seen: set[str] = set()
    for index, activity in enumerate(run):
        summary, activity_failures = _validate_activity(
            activity,
            root=project_path.parent,
            index=index,
            source_revision=source_revision,
            configuration_id=configuration_id,
            configuration_sha256=configuration_sha256,
        )
        activity_id = str(summary.get("id") or "")
        if activity_id:
            if activity_id in seen:
                failures.append(f"duplicate verification activity id: {activity_id}")
            seen.add(activity_id)
        activities.append(summary)
        failures.extend(activity_failures)
    failures.extend(_validate_gaps(verification.get("gaps")))

    return ValidationResult(
        profile=profile,
        status="PASS" if not failures else "FAIL",
        acceptance_claimed=not failures,
        activities=tuple(activities),
        failures=tuple(failures),
        limitations=(
            "mechanical acceptance does not establish semantic adequacy or functional-safety compliance",
        ),
    )
