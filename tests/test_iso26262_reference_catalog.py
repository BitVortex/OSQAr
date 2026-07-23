from __future__ import annotations

import copy
import json
import unicodedata
from importlib import resources
from pathlib import Path

import pytest

from tools.iso26262_reference_catalog import (
    CatalogValidationError,
    InventoryReference,
    KNOWN_TABLE_TOPICS,
    load_catalog,
    load_maintainer_inventory,
    render_catalog_rst,
    render_maintainer_inventory,
    scan_repository_references,
    scan_text_references,
    validate_catalog,
    validate_inventory_coverage,
)


ROOT = Path(__file__).resolve().parents[1]
MAINTAINER_INVENTORY_PATH = ROOT / "tests/data/iso26262_reference_inventory.json"
REQUIRED_ENTRY_FIELDS = {
    "reference_id",
    "edition",
    "part",
    "clause",
    "topic",
    "reference_kind",
    "project_paraphrase",
    "applicability",
}


def _valid_catalog() -> dict:
    return {
        "catalog_version": 1,
        "standard": "ISO 26262",
        "evidence_basis": "Controlled-copy-checked project paraphrases pending independent review.",
        "entries": [
            {
                "reference_id": "ISO26262-6:2018-T9",
                "edition": "2018",
                "part": 6,
                "clause": "9.4.4",
                "table": 9,
                "topic": "structural coverage metrics at software unit level",
                "reference_kind": "normative_recommendation",
                "project_paraphrase": "Use the table when planning structural coverage at software-unit level.",
                "applicability": "Software-unit verification activities selected by the project.",
            }
        ],
    }


def test_catalog_loads_and_has_expected_shape() -> None:
    catalog = load_catalog()
    validate_catalog(catalog)
    assert catalog["catalog_version"] == 1
    assert catalog["standard"] == "ISO 26262"
    assert catalog["evidence_basis"].strip()
    assert "Illustrative, incomplete" in catalog["evidence_basis"]
    assert "does not establish semantic validity" in catalog["evidence_basis"]
    assert catalog["entries"]
    assert all(REQUIRED_ENTRY_FIELDS <= entry.keys() for entry in catalog["entries"])


def test_catalog_uses_one_reference_kind_instead_of_overlapping_classifications() -> None:
    forbidden = {
        "normative_or_guidance",
        "requirement_or_recommendation",
        "reviewer_state",
        "prohibited_overstatement",
    }
    catalog = load_catalog()
    assert all(forbidden.isdisjoint(entry) for entry in catalog["entries"])
    assert {
        entry["reference_kind"] for entry in catalog["entries"]
    } == {
        "normative_requirement",
        "normative_recommendation",
        "guidance",
        "project_policy",
    }

    schema = json.loads(
        resources.files("osqar_data")
        .joinpath("standards/iso26262_reference_catalog.schema.json")
        .read_text(encoding="utf-8")
    )
    entry_schema = schema["$defs"]["reference"]
    assert forbidden.isdisjoint(entry_schema["required"])
    assert forbidden.isdisjoint(entry_schema["properties"])

    rendered = render_catalog_rst(catalog)
    assert "Reviewer state:" not in rendered
    assert "Do not claim:" not in rendered


def test_public_catalog_excludes_repository_occurrences_and_null_table_fields() -> None:
    catalog = load_catalog()
    assert MAINTAINER_INVENTORY_PATH.is_file()
    assert all("source_paths" not in entry for entry in catalog["entries"])
    assert all("table_entry" not in entry for entry in catalog["entries"])
    assert all(
        "table" not in entry or type(entry["table"]) is int and entry["table"] > 0
        for entry in catalog["entries"]
    )
    assert all(
        ("table" in entry) == ("-T" in entry["reference_id"])
        for entry in catalog["entries"]
        if entry["reference_kind"] != "project_policy"
    )
    rendered = render_catalog_rst(catalog)
    assert "OSQAr source paths:" not in rendered
    assert "do not require use" in rendered
    assert "skills or templates" in rendered


def test_catalog_is_available_as_an_installed_package_resource() -> None:
    catalog_resource = resources.files("osqar_data").joinpath(
        "standards/iso26262_reference_catalog.json"
    )
    schema_resource = resources.files("osqar_data").joinpath(
        "standards/iso26262_reference_catalog.schema.json"
    )

    assert json.loads(catalog_resource.read_text(encoding="utf-8"))["entries"]
    assert json.loads(schema_resource.read_text(encoding="utf-8"))["$schema"]


def test_validator_rejects_duplicate_reference_ids() -> None:
    catalog = _valid_catalog()
    catalog["entries"].append(copy.deepcopy(catalog["entries"][0]))

    with pytest.raises(CatalogValidationError, match="duplicate reference_id"):
        validate_catalog(catalog)


def test_catalog_schema_keeps_structural_and_callable_boundaries_explicit() -> None:
    schema = json.loads(
        resources.files("osqar_data")
        .joinpath("standards/iso26262_reference_catalog.schema.json")
        .read_text(encoding="utf-8")
    )
    entry_schema = schema["$defs"]["reference"]
    assert "source_paths" not in entry_schema["properties"]
    assert "table_entry" not in entry_schema["properties"]
    assert entry_schema["properties"]["table"] == {
        "type": "integer",
        "minimum": 1,
    }
    assert "table" not in entry_schema["required"]
    assert schema["properties"]["entries"]["uniqueItems"] is True
    assert entry_schema["properties"]["edition"] == {"const": "2018"}
    assert "reference_id uniqueness" in schema["$comment"]


@pytest.mark.parametrize(
    "field",
    ["edition", "clause", "reference_kind"],
)
def test_validator_rejects_missing_edition_clause_or_classification(field: str) -> None:
    catalog = _valid_catalog()
    del catalog["entries"][0][field]

    with pytest.raises(CatalogValidationError, match=field):
        validate_catalog(catalog)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("part", 0),
        ("part", 13),
        ("part", "6"),
        ("table", 0),
        ("table", -1),
        ("table", "9"),
        ("table", True),
    ],
)
def test_validator_rejects_malformed_parts_and_tables(field: str, value: object) -> None:
    catalog = _valid_catalog()
    catalog["entries"][0][field] = value

    with pytest.raises(CatalogValidationError, match=field):
        validate_catalog(catalog)


def test_validator_rejects_context_inconsistent_table_clause() -> None:
    catalog = _valid_catalog()
    catalog["entries"][0]["clause"] = "10.4.2"

    with pytest.raises(CatalogValidationError, match="Table 9 belongs to Clause 9.4.4"):
        validate_catalog(catalog)


def test_validator_rejects_missing_top_level_evidence_basis() -> None:
    catalog = _valid_catalog()
    del catalog["evidence_basis"]

    with pytest.raises(CatalogValidationError, match="evidence_basis"):
        validate_catalog(catalog)


def test_validator_rejects_boolean_catalog_version() -> None:
    catalog = _valid_catalog()
    catalog["catalog_version"] = True

    with pytest.raises(CatalogValidationError, match="catalog_version"):
        validate_catalog(catalog)


def test_validator_wraps_unhashable_classification_as_catalog_error() -> None:
    catalog = _valid_catalog()
    catalog["entries"][0]["reference_kind"] = ["normative_requirement"]

    with pytest.raises(CatalogValidationError, match="reference_kind"):
        validate_catalog(catalog)


def test_validator_rejects_unknown_table_mapping_and_rotated_known_topic() -> None:
    catalog = _valid_catalog()
    catalog["entries"][0].update(
        reference_id="ISO26262-8:2018-T9", part=8, clause="1"
    )
    with pytest.raises(CatalogValidationError, match="no controlled table mapping"):
        validate_catalog(catalog)

    catalog = _valid_catalog()
    catalog["entries"][0]["topic"] = KNOWN_TABLE_TOPICS[(6, 15)]
    with pytest.raises(CatalogValidationError, match="controlled topic"):
        validate_catalog(catalog)


def test_known_table_and_clause_mappings_are_conservative() -> None:
    entries = {entry["reference_id"]: entry for entry in load_catalog()["entries"]}

    expected = {
        "ISO26262-6:2018-T7": (7, "methods for software unit verification"),
        "ISO26262-6:2018-T8": (8, "deriving software unit test cases"),
        "ISO26262-6:2018-T9": (9, "structural coverage metrics"),
        "ISO26262-6:2018-T10": (10, "verification of software integration"),
        "ISO26262-6:2018-T11": (11, "software integration test cases"),
    }
    for reference_id, (table_number, topic) in expected.items():
        assert entries[reference_id]["table"] == table_number
        assert topic in entries[reference_id]["topic"]

    assert "software tools" in entries["ISO26262-8:2018-C11"]["topic"]
    change_analysis = entries["ISO26262-8:2018-C8.5.3"]
    assert change_analysis["topic"] == (
        "impact analysis and change request plan work products"
    )
    assert "change report" not in " ".join(
        change_analysis[field]
        for field in ("topic", "project_paraphrase", "applicability")
    ).lower()
    assert entries["ISO26262-10:2018-C9"]["reference_kind"] == "guidance"
    assert "Context" in entries["ISO26262-10:2018-C9"]["topic"]


def test_controlled_copy_table_13_to_15_topics_are_not_rotated() -> None:
    assert KNOWN_TABLE_TOPICS[(6, 13)] == "test environments for embedded-software testing"
    assert KNOWN_TABLE_TOPICS[(6, 14)] == "methods for tests of embedded software"
    assert KNOWN_TABLE_TOPICS[(6, 15)] == "methods for deriving embedded-software test cases"


def test_thresholds_and_other_unverified_claims_are_project_policy() -> None:
    policies = {
        entry["topic"]: entry
        for entry in load_catalog()["entries"]
        if entry["reference_kind"] == "project_policy"
    }

    for topic_fragment in (
        "numeric thresholds",
        "graph cardinalities",
        "coding restrictions",
        "GPG authenticity",
        "reproducibility",
        "assumption counts",
    ):
        entry = next(entry for topic, entry in policies.items() if topic_fragment in topic)
        assert entry["reference_kind"] == "project_policy"
        assert "ISO 26262 requires" not in entry["project_paraphrase"]


def test_generated_documentation_has_not_drifted() -> None:
    expected = render_catalog_rst(load_catalog())
    actual = (ROOT / "docs/iso26262_reference_catalog.rst").read_text(encoding="utf-8")

    assert actual == expected


def test_scanner_recognizes_common_clause_table_lists_and_ranges() -> None:
    references = scan_text_references(
        """ISO 26262-8:2018 Clause 11
ISO 26262-6 §5.4.3, Table 1
ISO 26262-6:2018 Tables 7/8 and 10-11
ISO 26262-8 §7, §8, §11
ISO 26262-4 §6.4.1-§6.4.3
""",
        source_path="skills/example/SKILL.md",
    )

    assert [(ref.part, ref.clause, ref.table) for ref in references] == [
        (8, "11", None),
        (6, "5.4.3", None),
        (6, None, 1),
        (6, None, 7),
        (6, None, 8),
        (6, None, 10),
        (6, None, 11),
        (8, "7", None),
        (8, "8", None),
        (8, "11", None),
        (4, "6.4.1", None),
        (4, "6.4.2", None),
        (4, "6.4.3", None),
    ]
    assert all(ref.edition == "2018" for ref in references)
    assert references[0].source_path == "skills/example/SKILL.md"
    assert references[0].line == 1
    assert references[0].column == 1


def test_repository_inventory_is_deterministic_complete_and_excludes_self_references() -> None:
    first = scan_repository_references(ROOT)
    second = scan_repository_references(ROOT)

    assert first == second
    assert len(first) == 147
    assert len({(ref.edition, ref.part, ref.clause, ref.table) for ref in first}) == 66
    assert len({ref.source_path for ref in first}) == 23
    assert not any(ref.source_path.startswith("tests/") for ref in first)
    assert not any("iso26262_reference_catalog" in ref.source_path for ref in first)
    reliance_reference = next(
        ref
        for ref in first
        if ref.source_path == "tools/tool_reliance.py"
        and ref.part == 8
        and ref.clause == "11"
    )
    assert reliance_reference.column == 43
    assert reliance_reference.raw == "ISO 26262-8:2018 Clause 11"
    scanned_paths = {ref.source_path for ref in first}
    assert "osqar_data/templates/asil-d_c/c/include/project.h" in scanned_paths
    assert "osqar_data/templates/asil-d_c/c/src/project.c" in scanned_paths


def test_packaged_catalog_covers_every_inventory_locator_and_exact_source_path() -> None:
    catalog = load_catalog()
    inventory = scan_repository_references(ROOT)
    declared = load_maintainer_inventory(MAINTAINER_INVENTORY_PATH)

    validate_inventory_coverage(catalog, inventory, declared)
    assert render_maintainer_inventory(catalog, inventory) == (
        MAINTAINER_INVENTORY_PATH.read_text(encoding="utf-8")
    )


def test_catalog_records_controlled_copy_boundary_without_stale_provenance() -> None:
    catalog = load_catalog()
    evidence_basis = catalog["evidence_basis"]
    rendered = render_catalog_rst(catalog)

    assert "controlled ISO 26262:2018 Parts 1–12 checks" in evidence_basis
    assert "illustrative, incomplete example catalog" in rendered
    assert "do not establish the semantic validity" in rendered
    assert "not an authoritative ISO 26262 source" in rendered
    assert "BitVortex" not in evidence_basis
    assert "Jeti" not in evidence_basis
    assert "unavailable" not in evidence_basis.lower()
    assert "extracts were unavailable" not in rendered.lower()
    assert all(
        entry["reference_kind"] == "normative_recommendation"
        for entry in catalog["entries"]
        if "table" in entry
    )


def test_inventory_coverage_rejects_uncatalogued_reference() -> None:
    inventory = [
        InventoryReference("docs/new.rst", 4, 3, "ISO 26262-5 §7.4", "2018", 5, "7.4", None)
    ]

    with pytest.raises(CatalogValidationError, match=r"uncatalogued.*ISO 26262-5:2018 Clause 7\.4"):
        validate_inventory_coverage(_valid_catalog(), inventory, {})


def test_inventory_coverage_rejects_wrong_source_paths() -> None:
    catalog = _valid_catalog()
    inventory = [
        InventoryReference("docs/actual.rst", 2, 1, "ISO 26262-6 Table 9", "2018", 6, None, 9)
    ]
    declared = {
        "inventory_version": 1,
        "catalog_version": 1,
        "entries": [
            {
                "reference_id": "ISO26262-6:2018-T9",
                "source_paths": ["docs/declared.rst"],
            }
        ],
    }

    with pytest.raises(CatalogValidationError, match=r"source_paths.*scanned repository citations"):
        validate_inventory_coverage(catalog, inventory, declared)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("ISO 26262-6:2011 Clause 9", "obsolete or unsupported edition 2011"),
        ("ISO 26262‑6:2011 Clause 9", "obsolete or unsupported edition 2011"),
        ("ISO\u00a026262‑6:2011 Clause 9", "obsolete or unsupported edition 2011"),
        ("ISO 26262−6:2011 Clause 9", "obsolete or unsupported edition 2011"),
        ("ISO 26262﹣6:2011 Clause 9", "obsolete or unsupported edition 2011"),
        ("ISO 26262－6:2011 Clause 9", "obsolete or unsupported edition 2011"),
        ("ISO 26262-6:2018x, Clause 8.4", "malformed ISO 26262 anchor"),
        ("ISO 26262-6:2018\u200dx, Clause 8.4", "malformed ISO 26262 anchor"),
        ("ISO 26262-6x, Clause 8.4", "malformed ISO 26262 anchor"),
        ("ISO 26262-6\u2060x, Clause 8.4", "malformed ISO 26262 anchor"),
        ("ISO 26262―8:2011 Clause 11", "malformed ISO 26262 anchor"),
        ("ISO 26262\u200d-8:2011 Clause 11", "malformed ISO 26262 anchor"),
        ("ISO 26262\u2028-8:2011 Clause 11", "malformed ISO 26262 anchor"),
        ("IS\tO 26262-6:2011 Clause 9", "malformed ISO 26262 anchor"),
        ("IS\rO 26262-6:2011 Clause 9", "malformed ISO 26262 anchor"),
        ("ISO 262\t62-6:2011 Clause 9", "malformed ISO 26262 anchor"),
        ("ISO 262\r62-6:2011 Clause 9", "malformed ISO 26262 anchor"),
        ("ISO 26262-13:2018 Clause 4", "part must be from 1 through 12"),
        ("ISO 26262-6:2018 Clause nine", "malformed ISO 26262 locator"),
        ("ISO 26262-6 Clause nine", "malformed ISO 26262 locator"),
        ("ISO 26262-6 Clause_9", "malformed ISO 26262 locator"),
        ("ISO 26262-6 ClauseX", "malformed ISO 26262 locator"),
        ("ISO 26262-6 Clause\u200d9", "malformed ISO 26262 locator"),
        ("ISO 26262-6 Table nine", "malformed ISO 26262 locator"),
        ("ISO 26262-6 Table_9", "malformed ISO 26262 locator"),
        ("ISO 26262-6 TablesX", "malformed ISO 26262 locator"),
        ("ISO 26262-6:2018 Table 0", "malformed ISO 26262 locator"),
        ("ISO 26262-6:2018 Clause 9.4.4x", "malformed ISO 26262 locator"),
        ("ISO 26262-6:2018 Table 9x", "malformed ISO 26262 locator"),
        ("ISO 26262-6:2018 Table 9.1", "malformed ISO 26262 locator"),
        ("ISO 26262-6:2018 Clause 9.4.4.x", "malformed ISO 26262 locator"),
        ("ISO 26262-6:2018 Clauses 9.4.2-", "malformed ISO 26262 locator"),
    ],
)
def test_scanner_rejects_obsolete_or_malformed_locators(text: str, message: str) -> None:
    with pytest.raises(CatalogValidationError, match=message):
        scan_text_references(text, source_path="docs/bad.rst")


def test_scanner_handles_unicode_hyphens_line_wrapping_and_word_boundaries() -> None:
    with pytest.raises(CatalogValidationError, match="obsolete or unsupported edition 2011"):
        scan_text_references(
            "ISO 26262‑6:2011 Clause 9", source_path="docs/obsolete.rst"
        )

    references = scan_text_references(
        "ISO 26262-5:2018,\nClause 7.4", source_path="docs/wrapped.rst"
    )
    assert [(ref.part, ref.clause, ref.table) for ref in references] == [
        (5, "7.4", None)
    ]
    for unrelated in (
        "CounterPart 6 Table 9",
        "IEC 61508 Part 6 Table 9",
        "IEC 61508-6:2010 Part 6 Clause 9.4.4",
        "This component is Part 6 Table 9 of an unrelated manual",
    ):
        assert scan_text_references(
            unrelated, source_path="docs/not-a-citation.rst"
        ) == []


def test_scanner_rejects_context_inconsistent_clause_table_pair() -> None:
    with pytest.raises(
        CatalogValidationError, match="Table 1 belongs to Clause 5.4.3"
    ):
        scan_text_references(
            "ISO 26262-6 §6.4.2, Table 1", source_path="docs/bad-pair.rst"
        )


@pytest.mark.parametrize(
    "text",
    [
        "ISO 26262-6:2018 Clauses 9.4.2, 9.4.4x",
        "ISO 26262-6:2018 Clauses 9.4.2 and 9.4.4x",
        "ISO 26262-6:2018 Clauses 9.4.2, 9.4.4.x",
        "ISO 26262-6:2018 Tables 7 and 9x",
        "ISO 26262-6:2018 Tables 7, 9.1",
        "ISO 26262-8:2018 Clauses 11/",
        "ISO 26262-8:2018 Clauses 11//",
        "ISO 26262-8:2018 Clauses 11/x",
        "ISO 26262-8:2018 Clauses 11,",
        "ISO 26262-8:2018 Clauses 11 and",
        "ISO 26262-8:2018 Clauses 11 and x",
        "ISO 26262-8:2018 Clauses 11, x",
        "ISO 26262-8:2018 Clauses 11, item 12",
        "ISO 26262-8:2018 Clauses 11–x",
        "ISO 26262-8:2018 Clause 11é",
        "ISO 26262-8:2018 Clause 11‐x",
        "ISO 26262-8:2018 Clause 11‑x",
        "ISO 26262-8:2018 Clause 11‒x",
        "ISO 26262-8:2018 Clause 11—x",
        "ISO 26262-8:2018 Clause 11−x",
        "ISO 26262-8:2018 Clause 11\u0301",
        "ISO 26262-8:2018 Clause 11\u200dx",
        "ISO 26262-8:2018 Clause 11\u2060x",
        "ISO 26262-8:2018 Clause 11\u001cx",
        "ISO 26262-8:2018 Clause 11\u001dx",
        "ISO 26262-8:2018 Clause 11\u001ex",
        "ISO 26262-8:2018 Clause 11\u001fx",
        "ISO 26262-8:2018 Clause 11\u2028x",
        "ISO 26262-8:2018 Clause 11\u2029x",
        "ISO 26262-6:2018 Clauses 9.4.4―x",
        "ISO 26262-8:2018 Clause 11..2",
        (
            "ISO 26262-8:2018 Clauses 11/ "
            "ISO 26262-8:2018 Clause 11"
        ),
    ],
)
def test_scanner_rejects_malformed_trailing_list_items(text: str) -> None:
    with pytest.raises(CatalogValidationError, match="malformed ISO 26262 locator"):
        scan_text_references(text, source_path="docs/probe.rst")


def test_scanner_rejects_every_unicode_dash_punctuation_locator_suffix() -> None:
    dash_characters = [
        chr(codepoint)
        for codepoint in range(0x110000)
        if unicodedata.category(chr(codepoint)) == "Pd"
    ]
    assert dash_characters
    for dash in dash_characters:
        with pytest.raises(CatalogValidationError, match="malformed ISO 26262 locator"):
            scan_text_references(
                f"ISO 26262-6:2018 Clause 9.4.4{dash}x",
                source_path="docs/unicode-dash-tail.rst",
            )


def test_scanner_accepts_spaced_double_section_marker() -> None:
    refs = scan_text_references(
        "ISO 26262-6:2018 §§ 9.4.2, 9.4.4",
        source_path="docs/probe.rst",
    )
    assert [(ref.clause, ref.table) for ref in refs] == [
        ("9.4.2", None),
        ("9.4.4", None),
    ]


def test_scanner_accepts_context_aware_locator_separators() -> None:
    refs = scan_text_references(
        "ISO 26262-8:2018 Clause 11, "
        "ISO 26262-6:2018 Clause 9.4.4; "
        "ISO 26262-8:2018 Clause 7/ Clause 11",
        source_path="docs/probe.rst",
    )
    assert [(ref.part, ref.clause) for ref in refs] == [
        (8, "11"),
        (6, "9.4.4"),
        (8, "7"),
        (8, "11"),
    ]


def test_catalog_rejects_context_inconsistent_reference_id() -> None:
    catalog = _valid_catalog()
    catalog["entries"][0]["reference_id"] = "ISO26262-8:2018-T9"

    with pytest.raises(CatalogValidationError, match="reference_id does not match locator"):
        validate_catalog(catalog)
