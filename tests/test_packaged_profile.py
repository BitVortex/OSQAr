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
