from __future__ import annotations

import json
from pathlib import Path

from tools import osqar_cmd_doctor, osqar_cmd_shipment
from tools.osqar_cli import main


def _write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _needs_with_claim(reference: str) -> dict[str, object]:
    return {
        "needs": [
            {
                "id": "STDCLAIM_SAMPLE",
                "standards_catalog": "sample",
                "standards_refs": [reference],
                "project_interpretation": "Project interpretation for this claim.",
                "applicability": "Applies to the reviewed component.",
                "realized_by": ["REQ_SAMPLE"],
            },
            {"id": "REQ_SAMPLE", "links": ["ARCH_SAMPLE"]},
            {"id": "ARCH_SAMPLE"},
        ]
    }


def _project_config() -> dict[str, object]:
    return {"standards": {"catalogs": [{"id": "sample", "source": "catalog.json"}]}}


def test_shipment_traceability_passes_explicit_project_config(
    tmp_path: Path, monkeypatch
) -> None:
    shipment = tmp_path / "shipment"
    _write_json(shipment / "needs.json", {"needs": []})
    config = _write_json(tmp_path / "project.json", {})
    captured: list[str] = []

    def fake_traceability_cli(argv: list[str]) -> int:
        captured.extend(argv)
        return 0

    monkeypatch.setattr(osqar_cmd_shipment, "traceability_cli", fake_traceability_cli)

    rc = main(
        [
            "shipment",
            "traceability",
            "--shipment",
            str(shipment),
            "--project-config",
            str(config),
        ]
    )

    assert rc == 0
    option = captured.index("--project-config")
    assert captured[option + 1] == str(config.resolve())


def test_shipment_traceability_without_config_remains_compatible_for_non_claims(
    tmp_path: Path,
) -> None:
    shipment = tmp_path / "shipment"
    _write_json(
        shipment / "needs.json",
        {
            "needs": [
                {"id": "REQ_SAMPLE", "links": ["ARCH_SAMPLE"]},
                {"id": "ARCH_SAMPLE"},
            ]
        },
    )

    assert main(["shipment", "traceability", "--shipment", str(shipment)]) == 0


def test_shipment_traceability_public_command_rejects_unknown_claim_reference(
    tmp_path: Path,
) -> None:
    shipment = tmp_path / "shipment"
    _write_json(shipment / "needs.json", _needs_with_claim("REF-UNKNOWN"))
    _write_json(tmp_path / "catalog.json", {"entries": [{"reference_id": "REF-KNOWN"}]})
    config = _write_json(tmp_path / "osqar_project.json", _project_config())
    report = tmp_path / "traceability-report.json"

    rc = main(
        [
            "shipment",
            "traceability",
            "--shipment",
            str(shipment),
            "--project-config",
            str(config),
            "--json-report",
            str(report),
        ]
    )

    assert rc == 1
    standards = json.loads(report.read_text(encoding="utf-8"))["standards_claims"]
    assert standards["violations"] == [
        {
            "rule": "STANDARDS_REFERENCE",
            "need_id": "STDCLAIM_SAMPLE",
            "message": "unknown reference sample:REF-UNKNOWN",
        }
    ]


def test_top_level_traceability_passes_project_config(tmp_path: Path) -> None:
    needs = _write_json(tmp_path / "needs.json", _needs_with_claim("REF-KNOWN"))
    _write_json(
        tmp_path / "catalog.json",
        {"entries": [{"reference_id": "REF-KNOWN"}]},
    )
    config = _write_json(tmp_path / "osqar_project.json", _project_config())
    report = tmp_path / "traceability-report.json"

    rc = main(
        [
            "traceability",
            str(needs),
            "--project-config",
            str(config),
            "--json-report",
            str(report),
        ]
    )

    assert rc == 0
    standards = json.loads(report.read_text(encoding="utf-8"))["standards_claims"]
    assert standards["violations"] == []


def test_shipment_verify_uses_shipped_project_config_for_standards_claims(
    tmp_path: Path,
) -> None:
    shipment = tmp_path / "shipment"
    _write_json(shipment / "needs.json", _needs_with_claim("REF-KNOWN"))
    _write_json(shipment / "catalog.json", {"entries": [{"reference_id": "REF-KNOWN"}]})
    _write_json(shipment / "osqar_project.json", _project_config())
    (shipment / "index.html").write_text("", encoding="utf-8")
    _write_json(shipment / "traceability_report.json", {})
    assert main(["shipment", "checksums", "--shipment", str(shipment), "generate"]) == 0

    report = tmp_path / "verify-traceability-report.json"
    rc = main(
        [
            "shipment",
            "verify",
            "--shipment",
            str(shipment),
            "--traceability",
            "--skip-code-trace",
            "--json-report",
            str(report),
        ]
    )

    assert rc == 0
    standards = json.loads(report.read_text(encoding="utf-8"))["standards_claims"]
    assert standards["violations"] == []
    assert standards["references"] == ["sample:REF-KNOWN"]


def test_shipment_prepare_uses_project_config_for_traceability(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "conf.py").write_text("", encoding="utf-8")
    (project / "index.rst").write_text("Project\n=======\n", encoding="utf-8")
    config = _write_json(project / "osqar_project.json", {})
    shipment = tmp_path / "shipment"
    captured: list[Path | None] = []

    monkeypatch.setattr(osqar_cmd_shipment.u, "run_hooks", lambda *args, **kwargs: 0)

    def fake_docs_build(*args, **kwargs) -> int:
        shipment.mkdir(parents=True, exist_ok=True)
        _write_json(shipment / "needs.json", {"needs": []})
        return 0

    monkeypatch.setattr(osqar_cmd_shipment.u, "run_docs_build", fake_docs_build)
    monkeypatch.setattr(
        osqar_cmd_shipment.u, "copy_bundle_sources_and_reports", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(osqar_cmd_shipment.u, "copy_test_reports", lambda *args, **kwargs: None)
    monkeypatch.setattr(osqar_cmd_shipment, "cmd_shipment_checksums", lambda args: 0)

    def fake_shipment_traceability(args) -> int:
        value = getattr(args, "project_config", None)
        captured.append(Path(value).resolve() if value else None)
        return 0

    monkeypatch.setattr(
        osqar_cmd_shipment, "cmd_shipment_traceability", fake_shipment_traceability
    )

    rc = main(
        [
            "shipment",
            "prepare",
            "--project",
            str(project),
            "--shipment",
            str(shipment),
            "--skip-build",
            "--skip-tests",
            "--skip-verification",
            "--skip-code-trace",
        ]
    )

    assert rc == 0
    assert captured == [config.resolve()]


def test_doctor_uses_project_config_for_traceability(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config = _write_json(project / "osqar_project.json", _project_config())
    shipment = tmp_path / "shipment"
    shipment.mkdir()
    (shipment / "index.html").write_text("", encoding="utf-8")
    _write_json(shipment / "needs.json", _needs_with_claim("REF-KNOWN"))
    captured: list[Path | None] = []

    def fake_doctor_traceability(**kwargs):
        value = kwargs.get("project_config")
        captured.append(Path(value).resolve() if value else None)
        return 0, {}

    monkeypatch.setattr(
        osqar_cmd_doctor, "_doctor_run_traceability", fake_doctor_traceability
    )

    main(
        [
            "doctor",
            "--project",
            str(project),
            "--shipment",
            str(shipment),
            "--skip-env-checks",
            "--skip-checksums",
        ]
    )

    assert captured == [config.resolve()]
