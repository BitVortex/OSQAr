from __future__ import annotations

import copy
import json
from importlib import resources

import pytest

from tools.tool_reliance import validate_tool_reliance_inventory


def _packaged_inventory() -> dict:
    resource = resources.files("osqar_data").joinpath(
        "governance/tool-reliance-v1.json"
    )
    return json.loads(resource.read_text(encoding="utf-8"))


def test_packaged_tool_reliance_inventory_is_valid_and_fail_closed() -> None:
    payload = _packaged_inventory()

    errors = validate_tool_reliance_inventory(payload)

    assert errors == []
    assert payload["schema"] == "osqar.tool-reliance.v1"
    assert payload["version_applicability"]["status"] == "unresolved"
    assert "review" not in json.dumps(payload, sort_keys=True).lower()
    assert all(item["reliance_permitted"] is False for item in payload["functions"])


@pytest.mark.parametrize("location", ["standards_basis", "function"])
def test_base_inventory_rejects_embedded_assessment_log_fields(location: str) -> None:
    payload = _packaged_inventory()
    if location == "standards_basis":
        payload["standards_basis"]["reviewer"] = "named person"
    else:
        payload["functions"][0]["review"] = {"status": "pending"}

    errors = validate_tool_reliance_inventory(payload)

    assert any("assessment-log fields belong outside" in error for error in errors)


def test_base_inventory_cannot_record_company_or_user_reliance_permission() -> None:
    payload = _packaged_inventory()
    candidate = next(
        item for item in payload["functions"] if item["boundary"] == "candidate"
    )
    candidate["reliance_permitted"] = True

    errors = validate_tool_reliance_inventory(payload)

    assert any("base framework cannot permit reliance" in error for error in errors)
    assert any("organization- or user-level assurance records" in error for error in errors)


def test_duplicate_function_ids_are_rejected() -> None:
    payload = _packaged_inventory()
    payload["functions"].append(copy.deepcopy(payload["functions"][0]))

    assert any(
        "duplicate function id" in error
        for error in validate_tool_reliance_inventory(payload)
    )


def test_function_model_requires_documented_reliance_argument_fields() -> None:
    payload = _packaged_inventory()
    payload["functions"][0].pop("owner", None)

    errors = validate_tool_reliance_inventory(payload)

    assert any("missing fields" in error and "owner" in error for error in errors)


def test_standards_basis_uses_technical_status_without_assessment_logs() -> None:
    payload = _packaged_inventory()
    assert payload["standards_basis"]["basis_status"] == "provisional"
    payload["standards_basis"]["basis_status"] = "approved"

    errors = validate_tool_reliance_inventory(payload)

    assert any("standards basis status" in error for error in errors)


def test_established_version_applicability_is_structurally_supported() -> None:
    payload = _packaged_inventory()
    payload["version_applicability"]["status"] = "established"

    assert validate_tool_reliance_inventory(payload) == []


def test_reliance_permitted_must_remain_a_boolean() -> None:
    payload = _packaged_inventory()
    payload["functions"][0]["reliance_permitted"] = "false"

    errors = validate_tool_reliance_inventory(payload)

    assert any("reliance_permitted must be boolean" in error for error in errors)
