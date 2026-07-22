from __future__ import annotations

import copy
import hashlib
import json
from importlib import resources
from pathlib import Path
from typing import Any

from tools.tool_reliance import validate_tool_reliance_inventory


def test_packaged_tool_reliance_inventory_is_valid_and_fail_closed() -> None:
    resource = resources.files("osqar_data").joinpath(
        "governance/tool-reliance-v1.json"
    )
    payload = json.loads(resource.read_text(encoding="utf-8"))

    errors = validate_tool_reliance_inventory(payload)

    assert errors == []
    assert payload["schema"] == "osqar.tool-reliance.v1"
    assert payload["version_applicability"]["status"] == "unresolved"
    assert all(not item["reliance_permitted"] for item in payload["functions"])


def test_reliance_requires_exact_version_evidence_and_independent_approval() -> None:
    payload = {
        "schema": "osqar.tool-reliance.v1",
        "version_applicability": {"status": "unresolved", "osqar_version": "*"},
        "standards_basis": {
            "reference": "ISO 26262-8:2018 Clause 11",
            "interpretation_status": "researched-pending-controlled-review",
        },
        "claim_boundary": "mechanical predicates only",
        "functions": [
            {
                "id": "checksum-verify",
                "command": "osqar checksum verify",
                "boundary": "candidate",
                "reliance_permitted": True,
                "tool_impact": "TI2-provisional",
                "tool_error_detection": "TD3-provisional",
                "tool_confidence_level": "TCL3-provisional",
                "erroneous_output": "false pass",
                "independent_detection": [],
                "evidence": [],
                "human_judgment": "artifact adequacy",
                "review": {"reviewer": "BitVortex", "status": "pending"},
            }
        ],
    }

    errors = validate_tool_reliance_inventory(payload)

    assert any("exact OSQAr version" in error for error in errors)
    assert any("independent detection" in error for error in errors)
    assert any("versioned evidence" in error for error in errors)
    assert any("independent approval" in error for error in errors)


def test_duplicate_function_ids_are_rejected() -> None:
    base = {
        "id": "impact",
        "command": "osqar impact",
        "boundary": "convenience",
        "reliance_permitted": False,
        "tool_impact": "not-classified",
        "tool_error_detection": "not-classified",
        "tool_confidence_level": "not-applicable",
        "erroneous_output": "incomplete candidate set",
        "independent_detection": [],
        "evidence": [],
        "human_judgment": "complete impact analysis",
        "review": {"reviewer": "BitVortex", "status": "pending"},
    }
    payload = {
        "schema": "osqar.tool-reliance.v1",
        "version_applicability": {"status": "unresolved", "osqar_version": "unresolved"},
        "standards_basis": {
            "reference": "ISO 26262-8:2018 Clause 11",
            "interpretation_status": "researched-pending-controlled-review",
        },
        "claim_boundary": "mechanical predicates only",
        "functions": [base, dict(base)],
    }

    assert any(
        "duplicate function id" in error
        for error in validate_tool_reliance_inventory(payload)
    )


def test_function_model_requires_documented_reliance_argument_fields() -> None:
    resource = resources.files("osqar_data").joinpath(
        "governance/tool-reliance-v1.json"
    )
    payload = json.loads(resource.read_text(encoding="utf-8"))
    payload["functions"][0].pop("owner", None)

    errors = validate_tool_reliance_inventory(payload)

    assert any("missing fields" in error and "owner" in error for error in errors)


def test_reliance_rejects_uncontrolled_applicability_and_approval() -> None:
    resource = resources.files("osqar_data").joinpath(
        "governance/tool-reliance-v1.json"
    )
    payload = json.loads(resource.read_text(encoding="utf-8"))
    candidate = next(
        item for item in payload["functions"] if item["boundary"] == "candidate"
    )
    payload["version_applicability"].update(
        status="reviewed",
        osqar_version="latest",
        qualification_profile_version="unresolved",
        supported_environments=[],
    )
    candidate.update(
        reliance_permitted=True,
        independent_detection=[" "],
        evidence=[" "],
        review={"reviewer": "anyone", "status": "approved"},
    )

    errors = validate_tool_reliance_inventory(copy.deepcopy(payload))

    assert any("exact OSQAr version" in error for error in errors)
    assert any("exact qualification profile" in error for error in errors)
    assert any("supported environment" in error for error in errors)
    assert any("controlled-copy-reviewed" in error for error in errors)
    assert any("independent detection entries" in error for error in errors)
    assert any("immutable evidence" in error for error in errors)
    assert any("designated reviewer" in error for error in errors)


def test_reliance_requires_resolved_use_case_argument() -> None:
    resource = resources.files("osqar_data").joinpath(
        "governance/tool-reliance-v1.json"
    )
    payload = json.loads(resource.read_text(encoding="utf-8"))
    candidate = next(
        item for item in payload["functions"] if item["boundary"] == "candidate"
    )
    payload["version_applicability"].update(
        status="reviewed",
        osqar_version="0.9.0",
        qualification_profile_version="1",
        supported_environments=["linux-x86_64"],
        python_version="3.13.5",
        dependency_set_revision="a" * 64,
    )
    payload["standards_basis"]["interpretation_status"] = "controlled-copy-reviewed"
    candidate.update(
        reliance_permitted=True,
        independent_detection=["independent oracle"],
        evidence=[
            {
                "id": "EV-1",
                "uri": "urn:osqar:evidence:EV-1",
                "revision": "abc123",
                "sha256": "b" * 64,
            }
        ],
        review={"reviewer": "BitVortex", "status": "approved"},
    )

    errors = validate_tool_reliance_inventory(payload)

    assert any("resolved lifecycle decision" in error for error in errors)
    assert any("resolved profile applicability" in error for error in errors)
    assert any("resolved environment applicability" in error for error in errors)
    assert any("immutable configuration" in error for error in errors)
    assert any("exact dependencies" in error for error in errors)
    assert any("anomaly disposition" in error for error in errors)


def _fully_controlled_reliance_payload(
    tmp_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    resource = resources.files("osqar_data").joinpath(
        "governance/tool-reliance-v1.json"
    )
    payload = json.loads(resource.read_text(encoding="utf-8"))
    candidate = next(
        item for item in payload["functions"] if item["boundary"] == "candidate"
    )
    payload["version_applicability"].update(
        status="reviewed",
        osqar_version="0.9.0",
        qualification_profile_version="1",
        supported_environments=["linux-x86_64"],
        python_version="3.13.5",
        dependency_set_revision="a" * 64,
    )
    payload["standards_basis"].update(
        interpretation_status="controlled-copy-reviewed",
        reviewer="BitVortex",
    )
    evidence_revision = "c" * 40
    evidence_artifact = tmp_path / "validation-evidence.json"
    evidence_artifact.write_text(
        json.dumps(
            {
                "schema": "osqar.validation-evidence.v1",
                "revision": evidence_revision,
                "result": "PASS",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    evidence_sha = hashlib.sha256(evidence_artifact.read_bytes()).hexdigest()
    candidate.update(
        reliance_permitted=True,
        input=["controlled input artifact"],
        output=["controlled output artifact"],
        exclusions=["no excluded paths"],
        independent_detection=["independent oracle"],
        evidence=[
            {
                "id": f"EV-1@{evidence_revision}",
                "uri": f"urn:sha256:{evidence_sha}",
                "revision": evidence_revision,
                "sha256": evidence_sha,
                "artifact": evidence_artifact.name,
            }
        ],
        lifecycle_decision={
            "id": "decision-1",
            "description": "Use output in reviewed impact analysis",
            "owner": "safety-manager",
            "work_product": "impact-analysis-v1",
        },
        profile_applicability=["qualification-v1"],
        environment_applicability=["linux-x86_64"],
        configuration={"identifier": "cfg-1", "sha256": "d" * 64},
        dependencies=[{"name": "python", "version": "3.13.5"}],
        known_anomalies=[
            {
                "affected_functions": [candidate["id"]],
                "versions": ["0.9.0"],
                "impact": "No known open anomaly affects the relied-upon predicate",
                "workaround": "none-required",
                "detection_status": "independently-reviewed",
                "prior_outputs_require_regeneration": False,
            }
        ],
        anomaly_disposition={"status": "reviewed", "review_revision": "e" * 40},
        assumptions=["Input schemas were independently reviewed"],
        operating_constraints=["Use only with qualification-v1"],
        residual_limitations=["Semantic adequacy requires human review"],
        revalidation_triggers=["OSQAr, dependency, profile, or environment change"],
        review={"reviewer": "BitVortex", "status": "approved"},
    )
    return payload, candidate


def test_reliance_rejects_self_designation_placeholder_environment_and_mutable_evidence(
    tmp_path: Path,
) -> None:
    payload, candidate = _fully_controlled_reliance_payload(tmp_path)

    def validate(value: Any) -> list[str]:
        return validate_tool_reliance_inventory(value, evidence_root=tmp_path)

    assert validate(payload) == []

    self_designated = copy.deepcopy(payload)
    self_designated["standards_basis"]["reviewer"] = "anyone"
    self_designated_candidate = next(
        item for item in self_designated["functions"] if item["id"] == candidate["id"]
    )
    self_designated_candidate["review"] = {"reviewer": "anyone", "status": "approved"}
    assert any(
        "designated reviewer" in error
        for error in validate(self_designated)
    )

    for placeholder in ("latest", "unresolved"):
        unresolved_environment = copy.deepcopy(payload)
        unresolved_environment["version_applicability"]["supported_environments"] = [
            placeholder
        ]
        assert any(
            "supported environment" in error
            for error in validate(unresolved_environment)
        )

    mutable_evidence = copy.deepcopy(payload)
    mutable_candidate = next(
        item for item in mutable_evidence["functions"] if item["id"] == candidate["id"]
    )
    mutable_candidate["evidence"] = [
        {
            "id": "anything",
            "uri": "anything",
            "revision": "anything",
            "sha256": "f" * 64,
        }
    ]
    assert any(
        "immutable evidence" in error
        for error in validate(mutable_evidence)
    )


def test_reliance_rejects_all_unresolved_decision_fields_and_missing_scope(
    tmp_path: Path,
) -> None:
    payload, candidate = _fully_controlled_reliance_payload(tmp_path)

    def validate(value: Any) -> list[str]:
        return validate_tool_reliance_inventory(value, evidence_root=tmp_path)

    assert validate(payload) == []

    for field in (
        "tool_impact",
        "tool_error_detection",
        "tool_confidence_level",
        "erroneous_output",
        "human_judgment",
        "owner",
    ):
        mutated = copy.deepcopy(payload)
        item = next(entry for entry in mutated["functions"] if entry["id"] == candidate["id"])
        item[field] = "unresolved"
        assert validate(mutated), field

    for field in ("input", "output", "exclusions"):
        mutated = copy.deepcopy(payload)
        item = next(entry for entry in mutated["functions"] if entry["id"] == candidate["id"])
        item[field] = []
        assert validate(mutated), field

    unresolved_configuration = copy.deepcopy(payload)
    item = next(
        entry
        for entry in unresolved_configuration["functions"]
        if entry["id"] == candidate["id"]
    )
    item["configuration"]["identifier"] = "unresolved"
    assert validate(unresolved_configuration)

    unresolved_anomaly_revision = copy.deepcopy(payload)
    item = next(
        entry
        for entry in unresolved_anomaly_revision["functions"]
        if entry["id"] == candidate["id"]
    )
    item["anomaly_disposition"]["review_revision"] = "unresolved"
    assert validate(unresolved_anomaly_revision)

    empty_anomaly_register = copy.deepcopy(payload)
    item = next(
        entry
        for entry in empty_anomaly_register["functions"]
        if entry["id"] == candidate["id"]
    )
    item["known_anomalies"] = []
    assert validate(empty_anomaly_register)

    for field, replacement in (
        ("affected_functions", ["unrelated-function"]),
        ("versions", ["9.9.9"]),
    ):
        mutated = copy.deepcopy(payload)
        item = next(entry for entry in mutated["functions"] if entry["id"] == candidate["id"])
        item["known_anomalies"][0][field] = replacement
        assert validate(mutated), field

    for placeholder in ("unresolved", "tbd", "none"):
        unresolved_detection = copy.deepcopy(payload)
        item = next(
            entry
            for entry in unresolved_detection["functions"]
            if entry["id"] == candidate["id"]
        )
        item["independent_detection"] = [placeholder]
        assert validate(unresolved_detection), placeholder

        unresolved_dependency = copy.deepcopy(payload)
        item = next(
            entry
            for entry in unresolved_dependency["functions"]
            if entry["id"] == candidate["id"]
        )
        item["dependencies"][0]["version"] = placeholder
        assert validate(unresolved_dependency), placeholder

    missing_artifact = copy.deepcopy(payload)
    item = next(
        entry
        for entry in missing_artifact["functions"]
        if entry["id"] == candidate["id"]
    )
    item["evidence"][0]["artifact"] = "missing-evidence.json"
    assert validate(missing_artifact)

    evidence_artifact = tmp_path / candidate["evidence"][0]["artifact"]
    evidence_artifact.write_text("{}\n", encoding="utf-8")
    assert validate(payload)
