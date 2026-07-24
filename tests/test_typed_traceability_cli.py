from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

from tools.osqar_cli import main


def _needs() -> list[dict]:
    return [
        {"id": "REQ_1", "title": "Requirement", "type": "requirement", "status": "active", "relations": {"allocated_to": ["ARCH_1"], "verified_by": ["VER_1"]}},
        {"id": "ARCH_1", "title": "Architecture", "type": "architecture", "status": "active", "relations": {"realized_by": ["API_1"]}},
        {"id": "API_1", "title": "api()", "type": "implementation", "kind": "api", "status": "active", "relations": {}},
        {"id": "VER_1", "title": "Verification", "type": "verification", "status": "active", "relations": {"produces": ["RESULT_1"]}},
        {"id": "RESULT_1", "title": "Result", "type": "result", "status": "passed", "evidence_state": "approved", "acceptance_activity": "unit", "relations": {"evidenced_by": ["EVID_1"]}},
        {"id": "EVID_1", "title": "Evidence", "type": "evidence", "status": "approved", "evidence_state": "approved", "acceptance_activity": "unit", "relations": {}},
        {"id": "SC_1", "title": "Claim", "type": "safety-case", "kind": "claim", "status": "supported", "relations": {"supported_by": ["EVID_1"]}},
    ]


SOURCE_REVISION = "a" * 40
CONFIGURATION_SHA256 = "b" * 64


def _evidence_args(tmp_path: Path) -> list[str]:
    result = tmp_path / "result.xml"
    result.write_text(
        "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
        "<testcase name='passes'/></testsuite>\n",
        encoding="utf-8",
    )
    project = tmp_path / "osqar_project.json"
    project.write_text(
        json.dumps(
            {
                "profile": "qualification",
                "source_revision": SOURCE_REVISION,
                "configuration_id": "qualification-config-v1",
                "configuration_sha256": CONFIGURATION_SHA256,
                "verification": {
                    "run": [{
                        "id": "unit", "required": True, "command": "pytest",
                        "activity_state": "completed",
                        "activity_history": ["planned", "ready", "running", "completed"],
                        "status": "passed", "evidence_state": "approved",
                        "applicability": "applicable", "report": result.name,
                        "report_format": "junit-xml",
                        "report_sha256": hashlib.sha256(result.read_bytes()).hexdigest(),
                        "source_revision": SOURCE_REVISION,
                        "configuration_id": "qualification-config-v1",
                        "configuration_sha256": CONFIGURATION_SHA256,
                        "environment": {"platform": "linux"},
                        "tool": {"name": "pytest", "version": "7.4", "available": True},
                        "findings": [], "thresholds": [],
                    }],
                    "gaps": {},
                },
            }
        ),
        encoding="utf-8",
    )
    return [
        "--evidence-project", str(project),
        "--source-revision", SOURCE_REVISION,
        "--configuration-sha256", CONFIGURATION_SHA256,
    ]


def test_cli_emits_typed_report_and_optional_api_artifact(tmp_path: Path) -> None:
    source = tmp_path / "needs.json"
    source.write_text(json.dumps({"needs": _needs()}), encoding="utf-8")
    report = tmp_path / "traceability.json"
    artifact = tmp_path / "api-requirements.csv"

    rc = main([
        "traceability",
        str(source),
        "--profile",
        "qualification",
        "--json-report",
        str(report),
        "--api-requirements-output",
        str(artifact),
        *_evidence_args(tmp_path),
    ])

    assert rc == 0
    assert json.loads(report.read_text())["status"] == "PASS"
    rows = list(csv.DictReader(artifact.open(encoding="utf-8")))
    assert rows[0]["API_ID"] == "API_1"
    assert rows[0]["Requirement_IDs"] == "REQ_1"
    assert "ARCH_1" not in artifact.read_text()
    audit = json.loads(artifact.with_suffix(".audit.json").read_text(encoding="utf-8"))
    assert audit["schema"] == "osqar.api-requirements-audit.v1"
    assert audit["paths"][0]["path"] == ["REQ_1", "ARCH_1", "API_1"]


def test_cli_does_not_emit_api_artifact_when_graph_fails(tmp_path: Path) -> None:
    needs = _needs()
    needs[0]["relations"]["allocated_to"] = []
    source = tmp_path / "needs.json"
    source.write_text(json.dumps({"needs": needs}), encoding="utf-8")
    artifact = tmp_path / "api-requirements.csv"
    audit = artifact.with_suffix(".audit.json")
    artifact.write_text("stale csv", encoding="utf-8")
    audit.write_text("stale audit", encoding="utf-8")

    rc = main([
        "traceability",
        str(source),
        "--profile",
        "qualification",
        "--api-requirements-output",
        str(artifact),
    ])

    assert rc == 1
    assert not artifact.exists()
    assert not audit.exists()


def test_cli_rejects_projection_under_basic_profile(tmp_path: Path) -> None:
    source = tmp_path / "needs.json"
    source.write_text(json.dumps({"needs": _needs()}), encoding="utf-8")
    artifact = tmp_path / "api.csv"

    rc = main([
        "traceability",
        str(source),
        "--api-requirements-output",
        str(artifact),
    ])

    assert rc == 2
    assert not artifact.exists()
    assert not artifact.with_suffix(".audit.json").exists()


def test_cli_rejects_output_alias_without_deleting_needs_input(tmp_path: Path) -> None:
    source = tmp_path / "needs.json"
    original = json.dumps({"needs": _needs()})
    source.write_text(original, encoding="utf-8")

    rc = main([
        "traceability",
        str(source),
        "--api-requirements-output",
        str(source),
    ])

    assert rc == 2
    assert source.read_text(encoding="utf-8") == original


def test_cli_rejects_hardlink_report_alias_without_modifying_input(tmp_path: Path) -> None:
    source = tmp_path / "needs.json"
    original = json.dumps({"needs": _needs()})
    source.write_text(original, encoding="utf-8")
    report = tmp_path / "report.json"
    os.link(source, report)

    rc = main([
        "traceability",
        str(source),
        "--profile",
        "qualification",
        "--json-report",
        str(report),
    ])

    assert rc == 2
    assert source.read_text(encoding="utf-8") == original
    assert report.samefile(source)


def test_cli_converts_output_write_failure_to_nonzero(tmp_path: Path) -> None:
    source = tmp_path / "needs.json"
    source.write_text(json.dumps({"needs": _needs()}), encoding="utf-8")
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")

    rc = main([
        "traceability",
        str(source),
        "--profile",
        "qualification",
        "--api-requirements-output",
        str(blocker / "api.csv"),
    ])

    assert rc == 2
