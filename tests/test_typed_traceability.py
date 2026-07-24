from __future__ import annotations

import hashlib
import json
from importlib import resources
from pathlib import Path

import pytest

from tools.typed_traceability import (
    project_api_requirement_paths,
    project_api_requirements,
    validate_typed_traceability,
)


def test_qualification_traceability_schema_is_packaged() -> None:
    schema = resources.files("osqar_data").joinpath("schemas/traceability-qualification-v1.json")
    assert schema.is_file()
    payload = json.loads(schema.read_text(encoding="utf-8"))
    assert payload["schema"] == "osqar.traceability-schema.v1"
    assert payload["relations"]["allocated_to"]["direction"] == "requirement->architecture"


def _valid_needs() -> list[dict]:
    return [
        {
            "id": "REQ_1",
            "title": "Parse input",
            "type": "requirement",
            "status": "active",
            "relations": {"allocated_to": ["ARCH_1"], "verified_by": ["VER_1"]},
        },
        {
            "id": "ARCH_1",
            "title": "Parser architecture",
            "type": "architecture",
            "status": "active",
            "relations": {"realized_by": ["API_PARSE"]},
        },
        {
            "id": "API_PARSE",
            "title": "parse()",
            "type": "implementation",
            "kind": "api",
            "status": "active",
            "relations": {},
        },
        {
            "id": "VER_1",
            "title": "Parser verification",
            "type": "verification",
            "status": "active",
            "relations": {"produces": ["RESULT_1"]},
        },
        {
            "id": "RESULT_1",
            "title": "Parser test result",
            "type": "result",
            "status": "passed",
            "evidence_state": "approved",
            "acceptance_activity": "unit",
            "relations": {"evidenced_by": ["EVID_1"]},
        },
        {
            "id": "EVID_1",
            "title": "JUnit report",
            "type": "evidence",
            "status": "approved",
            "evidence_state": "approved",
            "acceptance_activity": "unit",
            "relations": {},
        },
        {
            "id": "SC_1",
            "title": "Parser claim",
            "type": "safety-case",
            "kind": "claim",
            "status": "supported",
            "relations": {"supported_by": ["EVID_1"]},
        },
    ]


SOURCE_REVISION = "a" * 40
CONFIGURATION_SHA256 = "b" * 64


def _accepted_evidence(tmp_path: Path) -> dict:
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
    return {
        "evidence_project": project,
        "expected_source_revision": SOURCE_REVISION,
        "expected_configuration_sha256": CONFIGURATION_SHA256,
    }


def test_qualification_profile_passes_complete_typed_chain(tmp_path: Path) -> None:
    report = validate_typed_traceability(
        _valid_needs(), profile="qualification", **_accepted_evidence(tmp_path)
    )

    assert report.status == "PASS"
    assert report.profile == "qualification"
    assert report.schema == "osqar.traceability-report.v1"
    assert "requirement.allocated_to" in report.executed_rules


def test_qualification_rejects_local_pass_claim_without_framework_acceptance() -> None:
    report = validate_typed_traceability(_valid_needs(), profile="qualification")

    assert report.status == "FAIL"
    assert any("authoritative framework acceptance" in item for item in report.violations)
    assert any("EVID_1: evidence is not accepted" in item for item in report.violations)


def test_qualification_rejects_untrusted_framework_acceptance(tmp_path: Path) -> None:
    project = tmp_path / "project.json"
    project.write_text(
        json.dumps(
            {
                "profile": "qualification",
                "source_revision": "a" * 40,
                "configuration_id": "cfg",
                "configuration_sha256": "b" * 64,
                "verification": {"run": []},
            }
        ),
        encoding="utf-8",
    )

    report = validate_typed_traceability(
        _valid_needs(),
        profile="qualification",
        evidence_project=project,
        expected_source_revision="c" * 40,
        expected_configuration_sha256="d" * 64,
    )

    assert report.status == "FAIL"
    assert any("framework acceptance failed" in item for item in report.violations)


def test_qualification_binds_graph_evidence_to_accepted_activity(tmp_path: Path) -> None:
    evidence = _accepted_evidence(tmp_path)
    project = evidence["evidence_project"]
    payload = json.loads(project.read_text(encoding="utf-8"))
    payload["verification"]["run"][0]["id"] = "unrelated"
    project.write_text(json.dumps(payload), encoding="utf-8")

    report = validate_typed_traceability(
        _valid_needs(), profile="qualification", **evidence
    )

    assert report.status == "FAIL"
    assert any(
        "RESULT_1: acceptance activity 'unit' was not accepted" in item
        for item in report.violations
    )
    assert any(
        "EVID_1: acceptance activity 'unit' was not accepted" in item
        for item in report.violations
    )


def test_result_evidence_chain_cannot_cross_accepted_activities(tmp_path: Path) -> None:
    evidence = _accepted_evidence(tmp_path)
    project = evidence["evidence_project"]
    payload = json.loads(project.read_text(encoding="utf-8"))
    unrelated_report = tmp_path / "unrelated.xml"
    unrelated_report.write_text(
        "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
        "<testcase name='unrelated'/></testsuite>\n",
        encoding="utf-8",
    )
    unrelated = dict(payload["verification"]["run"][0])
    unrelated.update(
        {
            "id": "unrelated",
            "report": unrelated_report.name,
            "report_sha256": hashlib.sha256(unrelated_report.read_bytes()).hexdigest(),
        }
    )
    payload["verification"]["run"].append(unrelated)
    project.write_text(json.dumps(payload), encoding="utf-8")
    needs = _valid_needs()
    next(item for item in needs if item["id"] == "EVID_1")[
        "acceptance_activity"
    ] = "unrelated"

    report = validate_typed_traceability(needs, profile="qualification", **evidence)

    assert report.status == "FAIL"
    assert any(
        "RESULT_1: evidenced_by target EVID_1 binds activity 'unrelated'; expected 'unit'"
        in item
        for item in report.violations
    )


def test_sphinx_needs_native_relation_fields_are_supported(tmp_path: Path) -> None:
    needs = _valid_needs()
    for need in needs:
        relations = need.pop("relations")
        need.update(relations)

    evidence = _accepted_evidence(tmp_path)
    report = validate_typed_traceability(needs, profile="qualification", **evidence)
    rows = project_api_requirements(needs, profile="qualification", **evidence)

    assert report.status == "PASS"
    assert rows[0]["Requirement_IDs"] == "REQ_1"


def test_wrong_direction_cannot_satisfy_forward_relation() -> None:
    needs = _valid_needs()
    needs[0]["relations"]["allocated_to"] = []
    needs[1]["relations"]["allocated_to"] = ["REQ_1"]

    report = validate_typed_traceability(needs, profile="qualification")

    assert report.status == "FAIL"
    assert any("REQ_1: relation allocated_to requires at least 1" in item for item in report.violations)
    assert any("ARCH_1: relation allocated_to is not allowed" in item for item in report.violations)


def test_wrong_target_type_and_dead_link_fail() -> None:
    needs = _valid_needs()
    needs[0]["relations"]["verified_by"] = ["ARCH_1", "MISSING"]

    report = validate_typed_traceability(needs, profile="qualification")

    assert report.status == "FAIL"
    assert any("target ARCH_1 has type architecture" in item for item in report.violations)
    assert any("target MISSING does not exist" in item for item in report.violations)


def test_duplicate_ids_and_unknown_relations_fail() -> None:
    needs = _valid_needs()
    needs.append(dict(needs[0]))
    needs[0]["relations"]["anything"] = ["ARCH_1"]

    report = validate_typed_traceability(needs, profile="qualification")

    assert report.status == "FAIL"
    assert any("duplicate need id: REQ_1" in item for item in report.violations)
    assert any("unknown relation anything" in item for item in report.violations)


def test_unknown_controlled_kind_fails_vocabulary_closure() -> None:
    needs = _valid_needs()
    needs.append(
        {
            "id": "LM_1",
            "type": "lifecycle",
            "kind": "custom-state",
            "relations": {},
        }
    )

    report = validate_typed_traceability(needs, profile="qualification")

    assert report.status == "FAIL"
    assert any("LM_1: unsupported lifecycle kind" in item for item in report.violations)


def test_planned_or_unapproved_result_cannot_support_claim() -> None:
    needs = _valid_needs()
    result = next(item for item in needs if item["id"] == "RESULT_1")
    result["status"] = "not-run"
    result["evidence_state"] = "generated"
    claim = next(item for item in needs if item["id"] == "SC_1")
    claim["relations"]["supported_by"] = ["RESULT_1"]

    report = validate_typed_traceability(needs, profile="qualification")

    assert report.status == "FAIL"
    assert any("RESULT_1: result is not accepted" in item for item in report.violations)
    assert any("SC_1: target RESULT_1 is not accepted evidence" in item for item in report.violations)


@pytest.mark.parametrize("need_id", ["REQ_1", "ARCH_1", "API_PARSE", "VER_1"])
def test_participating_nodes_must_be_active(
    tmp_path: Path, need_id: str
) -> None:
    needs = _valid_needs()
    next(item for item in needs if item["id"] == need_id)["status"] = "retired"

    report = validate_typed_traceability(
        needs, profile="qualification", **_accepted_evidence(tmp_path)
    )

    assert report.status == "FAIL"
    assert any(f"{need_id}: participating node status 'retired'" in item for item in report.violations)


def test_target_cardinalities_reject_orphans_and_multiple_result_producers() -> None:
    needs = _valid_needs()
    needs.extend(
        [
            {
                "id": "ARCH_ORPHAN",
                "title": "Orphan architecture",
                "type": "architecture",
                "relations": {"realized_by": ["API_ORPHAN"]},
            },
            {
                "id": "API_ORPHAN",
                "title": "orphan()",
                "type": "implementation",
                "kind": "api",
                "relations": {},
            },
            {
                "id": "VER_2",
                "title": "Second producer",
                "type": "verification",
                "relations": {"produces": ["RESULT_1"]},
            },
        ]
    )

    report = validate_typed_traceability(needs, profile="qualification")

    assert report.status == "FAIL"
    assert any(
        "ARCH_ORPHAN: relation allocated_to requires at least 1 incoming" in item
        for item in report.violations
    )
    assert any(
        "RESULT_1: relation produces allows at most 1 incoming" in item
        for item in report.violations
    )


def test_api_audit_projection_preserves_full_intermediate_paths(tmp_path: Path) -> None:
    needs = _valid_needs()
    req = next(item for item in needs if item["id"] == "REQ_1")
    req["relations"]["allocated_to_api"] = ["API_PARSE"]

    paths = project_api_requirement_paths(
        needs, profile="qualification", **_accepted_evidence(tmp_path)
    )

    assert ["REQ_1", "API_PARSE"] in [item["path"] for item in paths]
    assert ["REQ_1", "ARCH_1", "API_PARSE"] in [item["path"] for item in paths]
    assert all(item["schema"] == "osqar.api-requirements-audit.v1" for item in paths)


def test_api_projection_traverses_backwards_and_omits_architecture(tmp_path: Path) -> None:
    needs = _valid_needs()
    rows = project_api_requirements(
        needs, profile="qualification", **_accepted_evidence(tmp_path)
    )

    assert rows == [
        {
            "API_ID": "API_PARSE",
            "API_Title": "parse()",
            "Requirement_IDs": "REQ_1",
            "Requirement_Titles": "Parse input",
            "Allocation_Status": "allocated",
            "Profile": "qualification",
            "Schema": "osqar.api-requirements.v1",
        }
    ]
    assert "ARCH_1" not in json.dumps(rows)


def test_api_projection_supports_direct_edges_deduplicates_and_reports_unallocated(
    tmp_path: Path,
) -> None:
    needs = _valid_needs()
    req = next(item for item in needs if item["id"] == "REQ_1")
    req["relations"]["allocated_to_api"] = ["API_PARSE"]
    needs.append(
        {
            "id": "API_UNUSED",
            "title": "unused()",
            "type": "implementation",
            "kind": "api",
            "status": "active",
            "relations": {},
        }
    )

    rows = project_api_requirements(
        needs, profile="qualification", **_accepted_evidence(tmp_path)
    )

    assert rows[0]["API_ID"] == "API_PARSE"
    assert rows[0]["Requirement_IDs"] == "REQ_1"
    assert rows[1]["API_ID"] == "API_UNUSED"
    assert rows[1]["Requirement_IDs"] == ""
    assert rows[1]["Allocation_Status"] == "unallocated"


def test_projection_rejects_basic_profile_and_invalid_graph() -> None:
    needs = _valid_needs()
    with pytest.raises(ValueError, match="require.*profile 'qualification'"):
        project_api_requirement_paths(needs, profile="basic")

    needs[0]["relations"]["allocated_to"] = []
    with pytest.raises(ValueError, match="typed traceability validation failed"):
        project_api_requirements(needs, profile="qualification")


def test_safety_case_self_support_is_not_accepted_evidence() -> None:
    needs = _valid_needs()
    claim = next(item for item in needs if item["id"] == "SC_1")
    claim["relations"]["supported_by"] = ["SC_1"]

    report = validate_typed_traceability(needs, profile="qualification")

    assert report.status == "FAIL"
    assert any("target SC_1 is not accepted evidence" in item for item in report.violations)
    assert any("traceability cycle: SC_1 -> SC_1" in item for item in report.violations)


def test_report_identifies_profile_and_schema_versions_and_basic_claim_is_bounded() -> None:
    report = validate_typed_traceability(_valid_needs(), profile="basic")
    payload = report.as_dict()

    assert payload["profile"] == "basic"
    assert payload["profile_version"] == 1
    assert payload["schema"] == "osqar.traceability-report.v1"
    assert payload["schema_version"] == 1
    assert payload["executed_rules"] == []
    assert "qualification" not in payload["claim"].lower()
    assert "bidirectional traceability" not in json.dumps(payload).lower()


def test_default_and_configured_api_prefixes_recognize_legacy_implementations(
    tmp_path: Path,
) -> None:
    needs = _valid_needs()
    implementation = next(item for item in needs if item["id"] == "API_PARSE")
    implementation.pop("kind")
    implementation["id"] = "IMPL_PARSE"
    next(item for item in needs if item["id"] == "ARCH_1")["relations"]["realized_by"] = [
        "IMPL_PARSE"
    ]
    evidence = _accepted_evidence(tmp_path)

    assert project_api_requirements(needs, profile="qualification", **evidence)[0][
        "API_ID"
    ] == "IMPL_PARSE"

    implementation["id"] = "SERVICE_PARSE"
    next(item for item in needs if item["id"] == "ARCH_1")["relations"]["realized_by"] = [
        "SERVICE_PARSE"
    ]
    rows = project_api_requirements(
        needs,
        profile="qualification",
        api_prefixes=("SERVICE_",),
        **evidence,
    )
    assert rows[0]["API_ID"] == "SERVICE_PARSE"
