from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools import traceability_check


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT / "osqar_data/templates/asil_example"
TEMPLATE_SHARED = TEMPLATE_ROOT / "shared"
TEMPLATE_LANGUAGES = {"c": TEMPLATE_ROOT / "c", "rust": TEMPLATE_ROOT / "rust"}


def _assert_claim_fields(claim: dict[str, object], expected: dict[str, object]) -> None:
    relation_fields = {"realized_by", "verified_by", "evidenced_by"}
    for field, expected_value in expected.items():
        if field in relation_fields:
            assert set(claim[field]) == set(expected_value)  # type: ignore[arg-type]
        else:
            assert claim[field] == expected_value


@pytest.mark.parametrize("language", ["c", "rust"])
def test_template_declares_packaged_iso26262_catalog(language: str) -> None:
    project = json.loads(
        (TEMPLATE_LANGUAGES[language] / "osqar_project.json").read_text(encoding="utf-8")
    )

    assert project["standards"]["catalogs"] == [
        {
            "id": "iso26262-2018",
            "source": "package:osqar_data/standards/iso26262_reference_catalog.json",
        }
    ]


def test_shared_showcase_content_is_language_neutral() -> None:
    shared_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(TEMPLATE_SHARED.glob("*.rst"))
    ).lower()

    for c_only_term in (
        "misra c",
        "cppcheck",
        "cmake",
        "gcov",
        "gcc",
        "null pointer",
        "valgrind",
    ):
        assert c_only_term not in shared_text
    assert not (TEMPLATE_SHARED / "04_implementation.rst").exists()


@pytest.mark.parametrize(
    ("language", "expected_terms"),
    [
        ("c", ("**language:** c", "**build system:** cmake")),
        ("rust", ("**language:** rust", "**build system:** cargo")),
    ],
)
def test_language_examples_describe_their_actual_implementation(
    language: str, expected_terms: tuple[str, ...]
) -> None:
    implementation = (
        TEMPLATE_LANGUAGES[language] / "04_implementation.rst"
    ).read_text(encoding="utf-8").lower()

    for expected in expected_terms:
        assert expected in implementation


def test_template_build_emits_generic_claim_fields_and_typed_relation(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    (source / "_static").mkdir()
    shutil.copyfile(TEMPLATE_LANGUAGES["c"] / "conf.py", source / "conf.py")
    (source / "index.rst").write_text(
        """Standards claim sentinel
========================

.. stdclaim:: Generic project interpretation
   :id: STDCLAIM_SENTINEL
   :standards_catalog: sentinel-catalog
   :standards_refs: SENTINEL-REF
   :project_interpretation: The project applies the referenced catalog entry.
   :applicability: Sentinel qualification scope.
   :realized_by: REQ_SENTINEL

.. need:: Sentinel requirement
   :id: REQ_SENTINEL

   The implementation shall satisfy the sentinel requirement.

.. evid:: Sentinel evidence
   :id: EVID_SENTINEL

   Evidence placeholder for the configuration sentinel.
""",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-W",
            "--keep-going",
            "-b",
            "needs",
            str(source),
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    payload = json.loads((output / "needs.json").read_text(encoding="utf-8"))
    version = payload["current_version"]
    needs = payload["versions"][version]["needs"]
    claim = needs["STDCLAIM_SENTINEL"]

    assert claim["standards_catalog"] == "sentinel-catalog"
    assert claim["standards_refs"] == "SENTINEL-REF"
    assert claim["project_interpretation"] == (
        "The project applies the referenced catalog entry."
    )
    assert claim["applicability"] == "Sentinel qualification scope."
    assert claim["realized_by"] == ["REQ_SENTINEL"]
    assert "REQ_SENTINEL" in needs
    assert needs["EVID_SENTINEL"]["type"] == "evid"


@pytest.mark.parametrize("language", ["c", "rust"])
def test_asil_target_showcase_builds_bounded_claims_and_pending_evidence(
    tmp_path: Path, language: str,
) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    shutil.copytree(TEMPLATE_SHARED, source)
    shutil.copytree(TEMPLATE_LANGUAGES[language], source, dirs_exist_ok=True)
    assert (source / "00_standards_claims.rst").is_file()

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-W",
            "--keep-going",
            "-b",
            "needs",
            str(source),
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "OSQAR_NO_DIAGRAMS": "1"},
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    payload = json.loads((output / "needs.json").read_text(encoding="utf-8"))
    version = payload["current_version"]
    needs = payload["versions"][version]["needs"]

    _assert_claim_fields(needs["STDCLAIM_SW_REQUIREMENTS"], {
        "standards_catalog": "iso26262-2018",
        "standards_refs": "ISO26262-6:2018-C6.4.1",
        "project_interpretation": (
            "This project treats requirements specification as a lifecycle activity; "
            "VER_UNIT_001 evaluates selected project requirements, but one activity "
            "does not prove the complete cited context."
        ),
        "applicability": "Draft software safety requirements for this example SEooC.",
        "realized_by": [
            "REQ_SSR_NOMINAL_001",
            "REQ_SSR_FAULT_001",
            "REQ_SSR_MEMORY_001",
        ],
        "verified_by": ["VER_UNIT_001"],
        "evidenced_by": [],
    })

    _assert_claim_fields(needs["STDCLAIM_STRUCTURAL_COVERAGE"], {
        "standards_catalog": "iso26262-2018",
        "standards_refs": "ISO26262-6:2018-T9",
        "project_interpretation": (
            "ISO 26262-6:2018 Table 9 is used here as a normative recommendation "
            "for structural coverage; the exact percentage thresholds are project "
            "policy, not thresholds prescribed by the cited table."
        ),
        "applicability": (
            "Draft software-unit structural-coverage criteria for safety-related "
            "source files."
        ),
        "realized_by": ["REQ_VER_COVERAGE_CRITERIA"],
        "verified_by": [
            "VER_COVERAGE_STMT",
            "VER_COVERAGE_BRANCH",
            "VER_COVERAGE_MCDC",
        ],
        "evidenced_by": ["EVID_COVERAGE_REPORT"],
    })

    _assert_claim_fields(needs["STDCLAIM_SEOOC_AOU"], {
        "standards_catalog": "iso26262-2018",
        "standards_refs": "ISO26262-10:2018-C9",
        "project_interpretation": (
            "ISO 26262-10:2018 Clause 9 is guidance for this project's selected "
            "SEooC assumptions of use; the linked lifecycle records are "
            "project-authored assumptions."
        ),
        "applicability": "Draft integration assumptions for this example SEooC.",
        "realized_by": [
            "LM_AOU_INTEGRATION",
            "LM_AOU_INPUTS",
            "LM_AOU_THREADING",
            "LM_AOU_ERROR_HANDLING",
        ],
        "verified_by": [],
        "evidenced_by": [],
    })

    coverage_requirement = needs["REQ_VER_COVERAGE_CRITERIA"]
    assert coverage_requirement["status"] == "draft"
    assert coverage_requirement["links"] == ["ARCH_DETERMINISTIC_FLOW"]

    assert needs["EVID_UNIT_TEST_RESULTS"]["type"] == "evid"
    assert needs["EVID_UNIT_TEST_RESULTS"]["status"] == "draft"
    assert needs["EVID_UNIT_TEST_RESULTS"]["links"] == ["VER_UNIT_001"]
    assert needs["EVID_COVERAGE_REPORT"]["type"] == "evid"
    assert needs["EVID_COVERAGE_REPORT"]["status"] == "draft"
    assert set(needs["EVID_COVERAGE_REPORT"]["links"]) == {
        "VER_COVERAGE_STMT",
        "VER_COVERAGE_BRANCH",
        "VER_COVERAGE_MCDC",
    }
    evidence_source = (source / "05_test_results.rst").read_text(encoding="utf-8")
    evidence_blocks: dict[str, str] = {}
    for evidence_id in ("EVID_UNIT_TEST_RESULTS", "EVID_COVERAGE_REPORT"):
        start = evidence_source.index(f":id: {evidence_id}")
        end = evidence_source.find("\n.. evid::", start)
        if end == -1:
            end = evidence_source.index("\n.. csv-table::", start)
        evidence_blocks[evidence_id] = evidence_source[start:end].lower()

    for evidence_text in evidence_blocks.values():
        assert "pending artifact expected" in evidence_text
        assert not any(
            fabricated in evidence_text
            for fabricated in ("sha256", "digest:", "test count", "passed", "approved")
        )

    boundary = " ".join(
        (source / "00_standards_claims.rst").read_text(encoding="utf-8").lower().split()
    )
    for required_text in (
        "iso 26262 is only the example catalog shipped with this template",
        "other catalogs can use stable ``reference_id`` values",
        "links are mechanical only",
        "no organization-specific disposition",
        "examples are deliberately incomplete",
        "do not establish compliance, qualification, certification, or safety",
        "general-purpose branch or block coverage data is not proof of mc/dc",
    ):
        assert required_text in boundary

    report = tmp_path / "traceability-report.json"
    assert (
        traceability_check.cli(
            [
                str(output / "needs.json"),
                "--project-config",
                str(source / "osqar_project.json"),
                "--json-report",
                str(report),
                "--no-enforce-req-traces-arch",
            ]
        )
        == 0
    )
    traceability = json.loads(report.read_text(encoding="utf-8"))
    assert traceability["violations"] == []
    assert traceability["standards_claims"]["counts"] == {
        "claims": 3,
        "catalogs": 1,
        "references": 3,
        "violations": 0,
    }
