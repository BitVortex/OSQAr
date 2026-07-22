from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import tools.osqar_evidence as evidence_module
from tools.osqar_evidence import (
    ALLOWED_ACTIVITY_STATES,
    ALLOWED_ACTIVITY_TRANSITIONS,
    validate_project,
)


SOURCE_REVISION = "a" * 40
CONFIGURATION_SHA256 = "b" * 64
CONFIGURATION_ID = "qualification-config-v1"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _qualification_project(tmp_path: Path) -> Path:
    report = tmp_path / "unit-results.xml"
    report.write_text(
        "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
        "<testcase name='passes'/></testsuite>\n",
        encoding="utf-8",
    )
    project = {
        "profile": "qualification",
        "source_revision": SOURCE_REVISION,
        "configuration_id": CONFIGURATION_ID,
        "configuration_sha256": CONFIGURATION_SHA256,
        "verification": {
            "run": [
                {
                    "id": "unit",
                    "required": True,
                    "command": "pytest",
                    "activity_state": "completed",
                    "activity_history": ["planned", "ready", "running", "completed"],
                    "status": "passed",
                    "evidence_state": "approved",
                    "applicability": "applicable",
                    "report": report.name,
                    "report_format": "junit-xml",
                    "report_sha256": _digest(report),
                    "source_revision": SOURCE_REVISION,
                    "configuration_id": CONFIGURATION_ID,
                    "configuration_sha256": CONFIGURATION_SHA256,
                    "environment": {"platform": "linux", "python": "3.13"},
                    "tool": {"name": "pytest", "version": "7.4", "available": True},
                    "findings": [],
                    "thresholds": [],
                }
            ],
            "gaps": {},
        },
    }
    path = tmp_path / "osqar_project.json"
    path.write_text(json.dumps(project), encoding="utf-8")
    return path


def _validate_qualification(project: Path):
    return validate_project(
        project,
        profile_name="qualification",
        expected_source_revision=SOURCE_REVISION,
        expected_configuration_sha256=CONFIGURATION_SHA256,
    )


def test_qualification_accepts_hash_bound_required_result(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    result = _validate_qualification(project)
    assert result.status == "PASS"
    assert result.failures == ()
    assert result.activities[0]["id"] == "unit"


def test_qualification_rejects_missing_report(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    data["verification"]["run"][0]["report"] = "missing.xml"
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("report does not exist" in failure for failure in result.failures)


def test_qualification_rejects_stale_report_hash(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    (tmp_path / "unit-results.xml").write_text("changed\n", encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("report_sha256 does not match" in failure for failure in result.failures)


def test_qualification_converts_report_read_error_to_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _qualification_project(tmp_path)

    def deny_read(_path: Path) -> str:
        raise PermissionError("injected report read failure")

    monkeypatch.setattr(evidence_module, "_sha256", deny_read)
    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("failed to read report" in failure for failure in result.failures)


def test_qualification_binds_activity_to_project_source_revision(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    data["verification"]["run"][0]["source_revision"] = "definitely-not-current-tree"
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("does not match project source_revision" in failure for failure in result.failures)


def test_qualification_requires_external_source_and_configuration_anchors(
    tmp_path: Path,
) -> None:
    project = _qualification_project(tmp_path)

    unanchored = validate_project(project, profile_name="qualification")
    assert unanchored.status == "FAIL"
    assert any("trusted expected_source_revision" in item for item in unanchored.failures)
    assert any("trusted expected_configuration_sha256" in item for item in unanchored.failures)

    data = json.loads(project.read_text())
    data["source_revision"] = "c" * 40
    data["configuration_sha256"] = "d" * 64
    activity = data["verification"]["run"][0]
    activity["source_revision"] = data["source_revision"]
    activity["configuration_sha256"] = data["configuration_sha256"]
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)
    assert result.status == "FAIL"
    assert any("does not match trusted expected_source_revision" in item for item in result.failures)
    assert any("does not match trusted expected_configuration_sha256" in item for item in result.failures)


def test_qualification_rejects_failed_required_activity(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    data["verification"]["run"][0]["status"] = "failed"
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("required activity is not accepted" in failure for failure in result.failures)


def test_qualification_rejects_non_boolean_activity_required(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    activity = data["verification"]["run"][0]
    activity.update(
        required=0,
        activity_state="waived",
        status="not-run",
        evidence_state="missing",
        activity_history=["planned", "waived"],
    )
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("required must be a boolean" in failure for failure in result.failures)


def test_qualification_rejects_duplicate_activity_ids(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    data["verification"]["run"].append(dict(data["verification"]["run"][0]))
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("duplicate verification activity id" in failure for failure in result.failures)


def test_qualification_requires_approved_deviation(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    activity = data["verification"]["run"][0]
    activity["status"] = "passed-with-deviation"
    activity["deviation"] = {"status": "open", "rationale": "pending"}
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("approved deviation" in failure for failure in result.failures)


def test_qualification_rejects_open_required_gap(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    data["verification"]["gaps"] = {
        "coverage": {"status": "open", "required": True, "rationale": "below target"}
    }
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("required gap remains open" in failure for failure in result.failures)


def test_qualification_rejects_non_boolean_gap_required(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    data["verification"]["gaps"] = {
        "coverage": {"status": "closed", "required": 0}
    }
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("gap coverage: required must be a boolean" in failure for failure in result.failures)


def test_qualification_rejects_superseded_evidence(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    data["verification"]["run"][0]["evidence_state"] = "superseded"
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("evidence is not approved" in failure for failure in result.failures)


def test_qualification_rejects_open_finding(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    data["verification"]["run"][0]["findings"] = [
        {"id": "F-1", "status": "open", "summary": "unresolved"}
    ]
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("finding F-1 is undispositioned" in failure for failure in result.failures)


def test_qualification_rejects_failed_threshold(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    data["verification"]["run"][0]["thresholds"] = [
        {"metric": "coverage", "observed": 95, "operator": ">=", "target": 100}
    ]
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("threshold failed" in failure for failure in result.failures)


def test_qualification_rejects_prohibited_state_transition(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    data["verification"]["run"][0]["activity_history"] = ["completed", "running"]
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("prohibited activity transition" in failure for failure in result.failures)


def test_qualification_rejects_history_without_planned_origin(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    data["verification"]["run"][0]["activity_history"] = ["completed"]
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("activity_history must begin with planned" in failure for failure in result.failures)


_HISTORY_TO_STATE = {
    "planned": ["planned"],
    "ready": ["planned", "ready"],
    "running": ["planned", "ready", "running"],
    "completed": ["planned", "ready", "running", "completed"],
    "failed": ["planned", "ready", "running", "failed"],
    "waived": ["planned", "waived"],
}


@pytest.mark.parametrize(
    ("previous", "current"),
    [
        (previous, current)
        for previous in sorted(ALLOWED_ACTIVITY_STATES)
        for current in sorted(ALLOWED_ACTIVITY_STATES)
    ],
)
def test_every_activity_transition_pair_is_enforced(
    tmp_path: Path, previous: str, current: str
) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    activity = data["verification"]["run"][0]
    activity.update(
        required=False,
        activity_state=current,
        activity_history=_HISTORY_TO_STATE[previous] + [current],
        status="not-run",
        evidence_state="missing",
    )
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)
    prohibited = any(
        "prohibited activity transition" in failure for failure in result.failures
    )

    assert prohibited is (current not in ALLOWED_ACTIVITY_TRANSITIONS[previous])


def test_qualification_rejects_unavailable_required_tool(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    data["verification"]["run"][0]["tool"]["available"] = False
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("required tool is unavailable" in failure for failure in result.failures)


def test_qualification_rejects_malformed_junit_report(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    activity = data["verification"]["run"][0]
    activity["report_format"] = "junit-xml"
    report = tmp_path / activity["report"]
    report.write_text("<testsuite>", encoding="utf-8")
    activity["report_sha256"] = _digest(report)
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("malformed junit-xml report" in failure for failure in result.failures)


@pytest.mark.parametrize(
    "xml",
    [
        "<testsuite tests='1' failures='1'><testcase><failure/></testcase></testsuite>",
        "<testsuite tests='1' skipped='1'><testcase><skipped/></testcase></testsuite>",
        "<testsuite tests='0' failures='0' errors='0' skipped='0'/>",
        "<not-junit/>",
        (
            "<testsuites tests='1' failures='1' errors='0' skipped='0'>"
            "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
            "<testcase name='contradiction'/></testsuite></testsuites>"
        ),
        (
            "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
            "<testcase name='hidden-failure'><failure/></testcase></testsuite>"
        ),
        (
            "<testsuites tests='1' failures='0' errors='0' skipped='0'>"
            "<testsuite tests='0' failures='0' errors='0' skipped='0'>"
            "<testsuite tests='1' failures='1' errors='0' skipped='0'>"
            "<testcase name='nested-failure'><failure/></testcase>"
            "</testsuite></testsuite>"
            "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
            "<testcase name='visible-pass'/></testsuite></testsuites>"
        ),
        (
            "<testsuites tests='1' failures='0' errors='0' skipped='0'>"
            "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
            "<testcase name='visible-pass'/>"
            "<testsuites tests='1' failures='1' errors='0' skipped='0'>"
            "<testsuite tests='1' failures='1' errors='0' skipped='0'>"
            "<testcase name='wrapped-failure'><failure/></testcase>"
            "</testsuite></testsuites></testsuite></testsuites>"
        ),
        (
            "<testsuites tests='1' failures='0' errors='0' skipped='0'>"
            "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
            "<testcase name='visible-pass'/></testsuite>"
            "<testcase name='misplaced-failure'><failure/></testcase>"
            "</testsuites>"
        ),
        (
            "<testsuites tests='1' failures='0' errors='0' skipped='0'>"
            "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
            "<testcase name='visible-pass'/></testsuite>"
            "<wrapper><testsuite tests='1' failures='1' errors='0' skipped='0'>"
            "<testcase name='hidden-failure'><failure/></testcase>"
            "</testsuite></wrapper></testsuites>"
        ),
    ],
)
def test_qualification_rejects_nonpassing_junit_report(tmp_path: Path, xml: str) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    activity = data["verification"]["run"][0]
    activity["report_format"] = "junit-xml"
    report = tmp_path / activity["report"]
    report.write_text(xml, encoding="utf-8")
    activity["report_sha256"] = _digest(report)
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("junit-xml report is not accepted" in failure for failure in result.failures)


def test_qualification_rejects_opaque_required_report(tmp_path: Path) -> None:
    project = _qualification_project(tmp_path)
    data = json.loads(project.read_text())
    activity = data["verification"]["run"][0]
    activity["report_format"] = "opaque"
    project.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_qualification(project)

    assert result.status == "FAIL"
    assert any("machine-interpretable report format" in failure for failure in result.failures)


def test_basic_reports_limitations_without_claiming_acceptance(tmp_path: Path) -> None:
    project = tmp_path / "osqar_project.json"
    project.write_text(json.dumps({"profile": "basic", "verification": {}}), encoding="utf-8")

    result = validate_project(project, profile_name="basic")

    assert result.status == "PASS"
    assert result.acceptance_claimed is False
    assert any("does not establish qualification evidence acceptance" in item for item in result.limitations)
