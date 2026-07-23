from __future__ import annotations

from importlib import resources

import yaml


def test_qualification_profile_is_packaged_and_versioned() -> None:
    profile_resource = resources.files("osqar_data").joinpath("profiles/qualification.yaml")
    assert profile_resource.is_file()
    profile = yaml.safe_load(profile_resource.read_text(encoding="utf-8"))
    assert profile["schema"] == "osqar.profile.v1"
    assert profile["id"] == "qualification"
    assert profile["evidence"]["accepted_result_states"] == [
        "passed",
        "passed-with-deviation",
    ]
    assert profile["shipment"]["closed_set"] is True


def test_qualification_profile_declares_optional_standards_claims_contract() -> None:
    profile_resource = resources.files("osqar_data").joinpath("profiles/qualification.yaml")
    profile = yaml.safe_load(profile_resource.read_text(encoding="utf-8"))

    assert profile["traceability"]["standards_claims"] == {
        "enabled": "optional",
        "catalog_entries_key": "entries",
        "catalog_reference_id_key": "reference_id",
        "claim_prefixes": ["STDCLAIM_"],
        "relation_targets": {
            "realized_by": ["REQ_", "LM_"],
            "verified_by": ["VER_"],
            "evidenced_by": ["EVID_"],
        },
    }
