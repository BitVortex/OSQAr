from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

import pytest

from tools import traceability_check


def _write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _valid_needs() -> dict[str, object]:
    return {
        "needs": [
            {
                "id": "STDCLAIM_SAMPLE",
                "standards_catalog": "sample",
                "standards_refs": ["REF-1"],
                "project_interpretation": "The project applies this reference mechanically.",
                "applicability": "Applies to this component.",
                "realized_by": ["REQ_SAMPLE"],
            },
            {"id": "REQ_SAMPLE", "links": ["ARCH_SAMPLE"]},
            {"id": "ARCH_SAMPLE"},
        ]
    }


def _valid_config(catalog_source: str = "catalog.json") -> dict[str, object]:
    return {"standards": {"catalogs": [{"id": "sample", "source": catalog_source}]}}


def _run_case(
    tmp_path: Path,
    *,
    config_value: object | None = None,
    catalog_value: object | None = None,
    needs_value: object | None = None,
) -> tuple[int, dict[str, object]]:
    needs = _write_json(tmp_path / "needs.json", needs_value or _valid_needs())
    if catalog_value is not None:
        _write_json(tmp_path / "catalog.json", catalog_value)
    config = _write_json(
        tmp_path / "project.json",
        _valid_config() if config_value is None else config_value,
    )
    report = tmp_path / "report.json"
    result = traceability_check.cli(
        [str(needs), "--project-config", str(config), "--json-report", str(report)]
    )
    return result, json.loads(report.read_text(encoding="utf-8"))["standards_claims"]


def test_valid_project_catalog_and_claim_graph_pass_and_report_boundary(
    tmp_path: Path,
) -> None:
    needs = _write_json(tmp_path / "needs.json", _valid_needs())
    _write_json(tmp_path / "catalog.json", {"entries": [{"reference_id": "REF-1"}]})
    config = _write_json(tmp_path / "project.json", _valid_config())
    report = tmp_path / "report.json"

    result = traceability_check.cli(
        [str(needs), "--project-config", str(config), "--json-report", str(report)]
    )

    assert result == 0
    standards = json.loads(report.read_text(encoding="utf-8"))["standards_claims"]
    assert standards["counts"] == {
        "catalogs": 1,
        "claims": 1,
        "references": 1,
        "violations": 0,
    }
    assert standards["catalogs"] == ["sample"]
    assert standards["references"] == ["sample:REF-1"]
    assert standards["violations"] == []
    assert standards["boundary"] == (
        "Mechanical validation only: catalog reference resolution and authored graph "
        "shape were checked; standards interpretation, applicability, adequacy, and "
        "compliance require project-authorized human review."
    )


def test_duplicate_catalog_ids_fail_closed(tmp_path: Path) -> None:
    needs = _write_json(tmp_path / "needs.json", _valid_needs())
    _write_json(tmp_path / "catalog.json", {"entries": [{"reference_id": "REF-1"}]})
    config_value = _valid_config()
    config_value["standards"]["catalogs"].append(  # type: ignore[index,union-attr]
        {"id": "sample", "source": "catalog.json"}
    )
    config = _write_json(tmp_path / "project.json", config_value)
    report = tmp_path / "report.json"

    result = traceability_check.cli(
        [str(needs), "--project-config", str(config), "--json-report", str(report)]
    )

    assert result == 1
    standards = json.loads(report.read_text(encoding="utf-8"))["standards_claims"]
    assert standards["counts"]["violations"] == 1
    assert standards["violations"][0]["rule"] == "STANDARDS_CATALOG_DECLARATION"
    assert "duplicate standards catalog id: sample" in standards["violations"][0]["message"]


CatalogMutation = Callable[[Path], tuple[object, Optional[object]]]


@pytest.mark.parametrize(
    ("mutation", "rule", "message"),
    [
        (lambda _p: ([], None), "STANDARDS_PROJECT_CONFIG", "project config must be a JSON object"),
        (lambda _p: ({}, None), "STANDARDS_PROJECT_CONFIG", "standards must be an object"),
        (lambda _p: ({"standards": []}, None), "STANDARDS_PROJECT_CONFIG", "standards must be an object"),
        (lambda _p: ({"standards": {}}, None), "STANDARDS_PROJECT_CONFIG", "standards.catalogs must be a list"),
        (lambda _p: ({"standards": {"catalogs": {}}}, None), "STANDARDS_PROJECT_CONFIG", "standards.catalogs must be a list"),
        (lambda _p: ({"standards": {"catalogs": [None]}}, None), "STANDARDS_CATALOG_DECLARATION", "catalog declaration 0 must be an object"),
        (lambda _p: ({"standards": {"catalogs": [{"source": "catalog.json"}]}}, None), "STANDARDS_CATALOG_DECLARATION", "catalog declaration 0 id must be a non-empty string"),
        (lambda _p: ({"standards": {"catalogs": [{"id": " ", "source": "catalog.json"}]}}, None), "STANDARDS_CATALOG_DECLARATION", "catalog declaration 0 id must be a non-empty string"),
        (lambda _p: ({"standards": {"catalogs": [{"id": 7, "source": "catalog.json"}]}}, None), "STANDARDS_CATALOG_DECLARATION", "catalog declaration 0 id must be a non-empty string"),
        (lambda _p: ({"standards": {"catalogs": [{"id": "sample"}]}}, None), "STANDARDS_CATALOG_DECLARATION", "catalog sample source must be a non-empty string"),
        (lambda _p: ({"standards": {"catalogs": [{"id": "sample", "source": ""}]}}, None), "STANDARDS_CATALOG_DECLARATION", "catalog sample source must be a non-empty string"),
        (lambda _p: ({"standards": {"catalogs": [{"id": "sample", "source": 7}]}}, None), "STANDARDS_CATALOG_DECLARATION", "catalog sample source must be a non-empty string"),
        (lambda _p: ({"standards": {"catalogs": [{"id": "sample", "source": "https://example.invalid/catalog.json"}]}}, None), "STANDARDS_CATALOG_DECLARATION", "unsupported standards catalog source"),
        (lambda _p: ({"standards": {"catalogs": [{"id": "sample", "source": "missing.json"}]}}, None), "STANDARDS_CATALOG_DECLARATION", "cannot read standards catalog sample"),
        (lambda _p: (_valid_config(), []), "STANDARDS_CATALOG_DECLARATION", "catalog sample must be a JSON object"),
        (lambda _p: (_valid_config(), {}), "STANDARDS_CATALOG_DECLARATION", "catalog sample entries must be a list"),
        (lambda _p: (_valid_config(), {"entries": {}}), "STANDARDS_CATALOG_DECLARATION", "catalog sample entries must be a list"),
        (lambda _p: (_valid_config(), {"entries": [None]}), "STANDARDS_CATALOG_ENTRY", "catalog sample entry 0 must be an object"),
        (lambda _p: (_valid_config(), {"entries": [{}]}), "STANDARDS_CATALOG_ENTRY", "catalog sample entry 0 reference_id must be a non-empty string"),
        (lambda _p: (_valid_config(), {"entries": [{"reference_id": " "}]}), "STANDARDS_CATALOG_ENTRY", "catalog sample entry 0 reference_id must be a non-empty string"),
        (lambda _p: (_valid_config(), {"entries": [{"reference_id": 7}]}), "STANDARDS_CATALOG_ENTRY", "catalog sample entry 0 reference_id must be a non-empty string"),
        (lambda _p: (_valid_config(), {"entries": [{"reference_id": "REF-1"}, {"reference_id": "REF-1"}]}), "STANDARDS_CATALOG_ENTRY", "duplicate reference_id REF-1 in catalog sample"),
    ],
)
def test_malformed_catalog_contract_fails_closed_with_deterministic_violation(
    tmp_path: Path,
    mutation: CatalogMutation,
    rule: str,
    message: str,
) -> None:
    config_value, catalog_value = mutation(tmp_path)
    result, standards = _run_case(
        tmp_path, config_value=config_value, catalog_value=catalog_value
    )

    assert result == 1
    assert standards["counts"]["violations"] >= 1  # type: ignore[index]
    assert standards["violations"][0]["rule"] == rule  # type: ignore[index]
    assert message in standards["violations"][0]["message"]  # type: ignore[index]


def _claim_with(field: str, value: object) -> dict[str, object]:
    needs = _valid_needs()
    claim = needs["needs"][0]  # type: ignore[index]
    claim[field] = value  # type: ignore[index]
    return needs


def _claim_without(field: str) -> dict[str, object]:
    needs = _valid_needs()
    claim = needs["needs"][0]  # type: ignore[index]
    del claim[field]  # type: ignore[index]
    return needs


@pytest.mark.parametrize(
    ("needs_value", "rule", "message"),
    [
        (_claim_without("standards_catalog"), "STANDARDS_CLAIM", "standards_catalog must be a non-empty string"),
        (_claim_with("standards_catalog", 7), "STANDARDS_CLAIM", "standards_catalog must be a non-empty string"),
        (_claim_with("standards_catalog", " "), "STANDARDS_CLAIM", "standards_catalog must be a non-empty string"),
        (_claim_without("standards_refs"), "STANDARDS_CLAIM", "standards_refs must be a non-empty string or list"),
        (_claim_with("standards_refs", []), "STANDARDS_CLAIM", "standards_refs must be a non-empty string or list"),
        (_claim_with("standards_refs", " "), "STANDARDS_CLAIM", "standards_refs must be a non-empty string or list"),
        (_claim_with("standards_refs", 7), "STANDARDS_CLAIM", "standards_refs must be a non-empty string or list"),
        (_claim_with("standards_refs", ["REF-1", ""]), "STANDARDS_CLAIM", "standards_refs item 1 must be a non-empty string"),
        (_claim_with("standards_refs", ["REF-1", 7]), "STANDARDS_CLAIM", "standards_refs item 1 must be a non-empty string"),
        (_claim_with("standards_catalog", "unknown"), "STANDARDS_REFERENCE", "unknown standards catalog: unknown"),
        (_claim_with("standards_refs", ["UNKNOWN"]), "STANDARDS_REFERENCE", "unknown reference sample:UNKNOWN"),
        (_claim_without("project_interpretation"), "STANDARDS_CLAIM", "project_interpretation must be a non-empty string"),
        (_claim_with("project_interpretation", " "), "STANDARDS_CLAIM", "project_interpretation must be a non-empty string"),
        (_claim_with("project_interpretation", 7), "STANDARDS_CLAIM", "project_interpretation must be a non-empty string"),
        (_claim_without("applicability"), "STANDARDS_CLAIM", "applicability must be a non-empty string"),
        (_claim_with("applicability", " "), "STANDARDS_CLAIM", "applicability must be a non-empty string"),
        (_claim_with("applicability", 7), "STANDARDS_CLAIM", "applicability must be a non-empty string"),
    ],
)
def test_malformed_claim_metadata_fails_closed(
    tmp_path: Path, needs_value: object, rule: str, message: str
) -> None:
    result, standards = _run_case(
        tmp_path,
        catalog_value={"entries": [{"reference_id": "REF-1"}]},
        needs_value=needs_value,
    )

    assert result == 1
    claim_violations = [
        item
        for item in standards["violations"]  # type: ignore[union-attr]
        if item["need_id"] == "STDCLAIM_SAMPLE"
    ]
    assert claim_violations[0]["rule"] == rule
    assert message in claim_violations[0]["message"]


def test_sphinx_string_reference_is_accepted_and_normalized(tmp_path: Path) -> None:
    result, standards = _run_case(
        tmp_path,
        catalog_value={"entries": [{"reference_id": "REF-1"}]},
        needs_value=_claim_with("standards_refs", "REF-1"),
    )

    assert result == 0
    assert standards["references"] == ["sample:REF-1"]


@pytest.mark.parametrize(
    "duplicate_refs",
    [
        ["REF-1", "REF-1"],
        ["REF-1", "  REF-1  "],
    ],
)
def test_duplicate_normalized_standards_refs_fail_without_duplicate_report_entries(
    tmp_path: Path, duplicate_refs: list[str]
) -> None:
    result, standards = _run_case(
        tmp_path,
        catalog_value={"entries": [{"reference_id": "REF-1"}]},
        needs_value=_claim_with("standards_refs", duplicate_refs),
    )

    assert result == 1
    assert standards["references"] == ["sample:REF-1"]
    assert standards["counts"]["references"] == 1
    assert standards["violations"] == [
        {
            "rule": "STANDARDS_CLAIM",
            "need_id": "STDCLAIM_SAMPLE",
            "message": "duplicate standards_refs item after normalization: REF-1",
        }
    ]


def test_reverse_relations_do_not_satisfy_authored_relation_requirement(
    tmp_path: Path,
) -> None:
    needs_value = _claim_without("realized_by")
    claim = needs_value["needs"][0]  # type: ignore[index]
    claim["realized_by_back"] = ["REQ_SAMPLE"]  # type: ignore[index]
    claim["verified_by_back"] = ["VER_SAMPLE"]  # type: ignore[index]
    claim["evidenced_by_back"] = ["EVID_SAMPLE"]  # type: ignore[index]

    result, standards = _run_case(
        tmp_path,
        catalog_value={"entries": [{"reference_id": "REF-1"}]},
        needs_value=needs_value,
    )

    assert result == 1
    assert standards["violations"] == [
        {
            "rule": "STANDARDS_CLAIM_RELATION",
            "need_id": "STDCLAIM_SAMPLE",
            "message": (
                "claim must author at least one relation in realized_by, verified_by, "
                "or evidenced_by"
            ),
        }
    ]


def test_authored_relation_rejects_non_string_scalar(tmp_path: Path) -> None:
    result, standards = _run_case(
        tmp_path,
        catalog_value={"entries": [{"reference_id": "REF-1"}]},
        needs_value=_claim_with("realized_by", 7),
    )

    assert result == 1
    assert standards["violations"] == [
        {
            "rule": "STANDARDS_CLAIM_RELATION",
            "need_id": "STDCLAIM_SAMPLE",
            "message": "realized_by must be a non-empty string or list",
        }
    ]


def test_typed_relation_dead_target_is_checked_when_generic_check_is_disabled(
    tmp_path: Path,
) -> None:
    needs = _write_json(
        tmp_path / "needs.json",
        _claim_with("realized_by", "REQ_MISSING"),
    )
    _write_json(tmp_path / "catalog.json", {"entries": [{"reference_id": "REF-1"}]})
    config = _write_json(tmp_path / "project.json", _valid_config())
    report = tmp_path / "report.json"

    result = traceability_check.cli(
        [
            str(needs),
            "--project-config",
            str(config),
            "--json-report",
            str(report),
            "--no-enforce-no-dead-links",
        ]
    )

    assert result == 1
    standards = json.loads(report.read_text(encoding="utf-8"))["standards_claims"]
    assert standards["violations"] == [
        {
            "rule": "STANDARDS_CLAIM_RELATION",
            "need_id": "STDCLAIM_SAMPLE",
            "message": "realized_by target does not resolve: REQ_MISSING",
        }
    ]


@pytest.mark.parametrize(
    ("field_name", "target", "allowed"),
    [
        ("realized_by", "ARCH_SAMPLE", "REQ_, LM_"),
        ("verified_by", "ARCH_SAMPLE", "VER_"),
        ("evidenced_by", "ARCH_SAMPLE", "EVID_"),
    ],
)
def test_typed_relation_rejects_resolved_target_with_wrong_prefix(
    tmp_path: Path, field_name: str, target: str, allowed: str
) -> None:
    needs_value = _claim_without("realized_by")
    claim = needs_value["needs"][0]  # type: ignore[index]
    claim[field_name] = [target]  # type: ignore[index]

    result, standards = _run_case(
        tmp_path,
        catalog_value={"entries": [{"reference_id": "REF-1"}]},
        needs_value=needs_value,
    )

    assert result == 1
    assert standards["violations"] == [
        {
            "rule": "STANDARDS_CLAIM_RELATION",
            "need_id": "STDCLAIM_SAMPLE",
            "message": f"{field_name} target {target} must use an allowed prefix: {allowed}",
        }
    ]


@pytest.mark.parametrize(
    ("field_name", "target"),
    [
        ("realized_by", "REQ_SAMPLE"),
        ("realized_by", "LM_SAMPLE"),
        ("verified_by", "VER_SAMPLE"),
        ("evidenced_by", "EVID_SAMPLE"),
    ],
)
def test_typed_relation_accepts_resolved_target_with_allowed_prefix(
    tmp_path: Path, field_name: str, target: str
) -> None:
    needs_value = _claim_without("realized_by")
    claim = needs_value["needs"][0]  # type: ignore[index]
    claim[field_name] = [target]  # type: ignore[index]
    existing_ids = {need["id"] for need in needs_value["needs"]}  # type: ignore[index,union-attr]
    if target not in existing_ids:
        needs_value["needs"].append({"id": target})  # type: ignore[index,union-attr]

    result, standards = _run_case(
        tmp_path,
        catalog_value={"entries": [{"reference_id": "REF-1"}]},
        needs_value=needs_value,
    )

    assert result == 0
    assert standards["violations"] == []


@pytest.mark.parametrize(
    ("field_name", "target", "duplicate_target"),
    [
        ("realized_by", "REQ_SAMPLE", "REQ_SAMPLE"),
        ("realized_by", "REQ_SAMPLE", "  REQ_SAMPLE  "),
        ("verified_by", "VER_SAMPLE", "VER_SAMPLE"),
        ("verified_by", "VER_SAMPLE", "  VER_SAMPLE  "),
        ("evidenced_by", "EVID_SAMPLE", "EVID_SAMPLE"),
        ("evidenced_by", "EVID_SAMPLE", "  EVID_SAMPLE  "),
    ],
)
def test_duplicate_normalized_authored_relation_targets_fail_closed(
    tmp_path: Path, field_name: str, target: str, duplicate_target: str
) -> None:
    needs_value = _claim_without("realized_by")
    claim = needs_value["needs"][0]  # type: ignore[index]
    claim[field_name] = [target, duplicate_target]  # type: ignore[index]
    existing_ids = {need["id"] for need in needs_value["needs"]}  # type: ignore[index,union-attr]
    if target not in existing_ids:
        needs_value["needs"].append({"id": target})  # type: ignore[index,union-attr]

    result, standards = _run_case(
        tmp_path,
        catalog_value={"entries": [{"reference_id": "REF-1"}]},
        needs_value=needs_value,
    )

    assert result == 1
    assert standards["violations"] == [
        {
            "rule": "STANDARDS_CLAIM_RELATION",
            "need_id": "STDCLAIM_SAMPLE",
            "message": f"duplicate {field_name} target after normalization: {target}",
        }
    ]


@pytest.mark.parametrize(
    ("field_name", "target"),
    [
        ("realized_by", "REQ_SAMPLE"),
        ("verified_by", "VER_SAMPLE"),
        ("evidenced_by", "EVID_SAMPLE"),
    ],
)
def test_typed_relation_list_entries_must_be_nonempty_strings(
    tmp_path: Path, field_name: str, target: str
) -> None:
    needs_value = _claim_without("realized_by")
    claim = needs_value["needs"][0]  # type: ignore[index]
    claim[field_name] = [target, "", 7]  # type: ignore[index]
    existing_ids = {need["id"] for need in needs_value["needs"]}  # type: ignore[index,union-attr]
    if target not in existing_ids:
        needs_value["needs"].append({"id": target})  # type: ignore[index,union-attr]

    result, standards = _run_case(
        tmp_path,
        catalog_value={"entries": [{"reference_id": "REF-1"}]},
        needs_value=needs_value,
    )

    assert result == 1
    assert standards["violations"] == [
        {
            "rule": "STANDARDS_CLAIM_RELATION",
            "need_id": "STDCLAIM_SAMPLE",
            "message": f"{field_name} item 1 must be a non-empty string",
        },
        {
            "rule": "STANDARDS_CLAIM_RELATION",
            "need_id": "STDCLAIM_SAMPLE",
            "message": f"{field_name} item 2 must be a non-empty string",
        },
    ]


def test_packaged_iso26262_catalog_and_real_reference_resolve(tmp_path: Path) -> None:
    needs_value = _valid_needs()
    claim = needs_value["needs"][0]  # type: ignore[index]
    claim["standards_catalog"] = "iso26262"  # type: ignore[index]
    claim["standards_refs"] = ["ISO26262-2:2018-C6.4.6"]  # type: ignore[index]
    config = _valid_config(
        "package:osqar_data/standards/iso26262_reference_catalog.json"
    )
    config["standards"]["catalogs"][0]["id"] = "iso26262"  # type: ignore[index]

    result, standards = _run_case(
        tmp_path,
        config_value=config,
        needs_value=needs_value,
    )

    assert result == 0
    assert standards["catalogs"] == ["iso26262"]
    assert standards["references"] == ["iso26262:ISO26262-2:2018-C6.4.6"]
    assert standards["counts"]["violations"] == 0


def test_no_standards_claim_without_project_config_preserves_basic_behavior(
    tmp_path: Path,
) -> None:
    needs_value = _valid_needs()
    needs_value["needs"] = needs_value["needs"][1:]  # type: ignore[index]
    needs = _write_json(tmp_path / "needs.json", needs_value)
    report = tmp_path / "report.json"

    result = traceability_check.cli([str(needs), "--json-report", str(report)])

    assert result == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["standards_claims"]["counts"] == {
        "catalogs": 0,
        "claims": 0,
        "references": 0,
        "violations": 0,
    }
    assert payload["standards_claims"]["violations"] == []


def test_validation_violation_replaces_stale_pass_report_exactly(tmp_path: Path) -> None:
    needs = _write_json(
        tmp_path / "needs.json",
        _claim_with("realized_by", "REQ_MISSING"),
    )
    _write_json(tmp_path / "catalog.json", {"entries": [{"reference_id": "REF-1"}]})
    config = _write_json(tmp_path / "project.json", _valid_config())
    report = tmp_path / "report.json"
    stale = {"schema": "osqar.traceability-report.v1", "status": "PASS"}
    report.write_text(json.dumps(stale), encoding="utf-8")

    result = traceability_check.cli(
        [str(needs), "--project-config", str(config), "--json-report", str(report)]
    )

    assert result == 1
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload != stale
    expected = {
        "rule": "STANDARDS_CLAIM_RELATION",
        "need_id": "STDCLAIM_SAMPLE",
        "message": "realized_by target does not resolve: REQ_MISSING",
    }
    assert payload["standards_claims"]["violations"] == [expected]
    assert payload["standards_claims"]["counts"]["violations"] == 1
    assert payload["violations"] == [expected]
    assert payload["meta"]["counts"]["violations_total"] == 1


def test_malformed_project_config_invalidates_stale_pass_report(
    tmp_path: Path,
) -> None:
    needs = _write_json(tmp_path / "needs.json", _valid_needs())
    config = tmp_path / "project.json"
    config.write_text("not json\n", encoding="utf-8")
    report = tmp_path / "report.json"
    report.write_text(
        '{"schema":"osqar.traceability-report.v1","status":"PASS"}\n',
        encoding="utf-8",
    )

    result = traceability_check.cli(
        [str(needs), "--project-config", str(config), "--json-report", str(report)]
    )

    assert result == 2
    assert not report.exists()


def test_report_equal_to_malformed_project_config_is_rejected_without_modification(
    tmp_path: Path,
) -> None:
    needs = _write_json(tmp_path / "needs.json", _valid_needs())
    config = tmp_path / "project.json"
    original = b"not json\n"
    config.write_bytes(original)

    result = traceability_check.cli(
        [str(needs), "--project-config", str(config), "--json-report", str(config)]
    )

    assert result == 2
    assert config.read_bytes() == original


def test_report_equal_to_declared_project_catalog_is_rejected_without_modification(
    tmp_path: Path,
) -> None:
    needs = _write_json(tmp_path / "needs.json", _valid_needs())
    config = _write_json(tmp_path / "project.json", _valid_config())
    catalog = tmp_path / "catalog.json"
    original = b'{"entries":[{"reference_id":"REF-1"}]}\n'
    catalog.write_bytes(original)

    result = traceability_check.cli(
        [str(needs), "--project-config", str(config), "--json-report", str(catalog)]
    )

    assert result == 2
    assert catalog.read_bytes() == original
