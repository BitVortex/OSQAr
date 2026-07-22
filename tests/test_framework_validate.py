from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import tools.osqar_evidence as evidence_module
from tools.osqar_cli import main


SOURCE_REVISION = "a" * 40
CONFIGURATION_SHA256 = "b" * 64
CONFIGURATION_ID = "qualification-config-v1"


def _project(tmp_path: Path) -> Path:
    report = tmp_path / "result.xml"
    report.write_text(
        "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
        "<testcase name='passes'/></testsuite>\n",
        encoding="utf-8",
    )
    data = {
        "profile": "qualification",
        "source_revision": SOURCE_REVISION,
        "configuration_id": CONFIGURATION_ID,
        "configuration_sha256": CONFIGURATION_SHA256,
        "verification": {
            "run": [
                {
                    "id": "unit",
                    "required": True,
                    "command": "pytest",
                    "activity_state": "completed",
                    "activity_history": ["planned", "ready", "running", "completed"],
                    "status": "passed",
                    "evidence_state": "approved",
                    "applicability": "applicable",
                    "report": report.name,
                    "report_format": "junit-xml",
                    "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
                    "source_revision": SOURCE_REVISION,
                    "configuration_id": CONFIGURATION_ID,
                    "configuration_sha256": CONFIGURATION_SHA256,
                    "environment": {"platform": "linux"},
                    "tool": {"name": "pytest", "version": "7.4", "available": True},
                    "findings": [],
                    "thresholds": [],
                }
            ],
            "gaps": {},
        },
    }
    path = tmp_path / "osqar_project.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_framework_validate_writes_machine_readable_report(tmp_path: Path) -> None:
    project = _project(tmp_path)
    output = tmp_path / "acceptance.json"

    rc = main(
        [
            "framework",
            "validate",
            "--profile",
            "qualification",
            "--source-revision",
            SOURCE_REVISION,
            "--configuration-sha256",
            CONFIGURATION_SHA256,
            "--project",
            str(project),
            "--report-json",
            str(output),
        ]
    )

    assert rc == 0
    report = json.loads(output.read_text())
    assert report["schema"] == "osqar.acceptance-report.v1"
    assert report["profile"] == "qualification"
    assert report["status"] == "PASS"


def test_framework_validate_returns_nonzero_on_acceptance_failure(tmp_path: Path) -> None:
    project = _project(tmp_path)
    data = json.loads(project.read_text())
    data["verification"]["run"][0]["status"] = "not-run"
    project.write_text(json.dumps(data), encoding="utf-8")

    rc = main(
        [
            "framework",
            "validate",
            "--profile",
            "qualification",
            "--source-revision",
            SOURCE_REVISION,
            "--configuration-sha256",
            CONFIGURATION_SHA256,
            "--project",
            str(project),
        ]
    )

    assert rc == 1


def test_framework_validate_rejects_profile_mismatch(tmp_path: Path) -> None:
    project = _project(tmp_path)

    rc = main(["framework", "validate", "--profile", "basic", "--project", str(project)])

    assert rc == 1


def test_framework_validate_handles_unwritable_report_target(tmp_path: Path) -> None:
    project = _project(tmp_path)
    output = tmp_path / "acceptance.json"
    output.mkdir()

    rc = main(
        [
            "framework",
            "validate",
            "--profile",
            "qualification",
            "--source-revision",
            SOURCE_REVISION,
            "--configuration-sha256",
            CONFIGURATION_SHA256,
            "--project",
            str(project),
            "--report-json",
            str(output),
        ]
    )

    assert rc == 2


def test_framework_validate_replaces_stale_success_after_report_read_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _project(tmp_path)
    output = tmp_path / "acceptance.json"
    output.write_text('{"status":"PASS","acceptance_claimed":true}\n', encoding="utf-8")

    def deny_read(_path: Path) -> str:
        raise PermissionError("injected report read failure")

    monkeypatch.setattr(evidence_module, "_sha256", deny_read)
    rc = main(
        [
            "framework",
            "validate",
            "--profile",
            "qualification",
            "--source-revision",
            SOURCE_REVISION,
            "--configuration-sha256",
            CONFIGURATION_SHA256,
            "--project",
            str(project),
            "--report-json",
            str(output),
        ]
    )

    assert rc == 1
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "FAIL"
    assert report["acceptance_claimed"] is False


def test_framework_validate_removes_outputs_after_publication_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _project(tmp_path)
    output = tmp_path / "acceptance.json"
    output.write_text('{"status":"PASS","acceptance_claimed":true}\n', encoding="utf-8")
    original_write_text = Path.write_text

    def fail_temporary_write(
        self: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> int:
        if self.name == ".acceptance.json.tmp":
            raise OSError("injected publication failure")
        return original_write_text(self, data, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "write_text", fail_temporary_write)
    rc = main(
        [
            "framework",
            "validate",
            "--profile",
            "qualification",
            "--source-revision",
            SOURCE_REVISION,
            "--configuration-sha256",
            CONFIGURATION_SHA256,
            "--project",
            str(project),
            "--report-json",
            str(output),
        ]
    )

    assert rc == 2
    assert not output.exists()
    assert not output.with_name(".acceptance.json.tmp").exists()


def test_framework_validate_contains_cleanup_failure_and_neutralizes_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _project(tmp_path)
    output = tmp_path / "acceptance.json"
    temporary = output.with_name(".acceptance.json.tmp")
    original_unlink = Path.unlink

    def fail_replace(self: Path, target: Path) -> Path:
        raise OSError("injected replacement failure")

    def fail_temporary_unlink(self: Path, missing_ok: bool = False) -> None:
        if self == temporary and self.exists():
            raise OSError("injected cleanup failure")
        original_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "replace", fail_replace)
    monkeypatch.setattr(Path, "unlink", fail_temporary_unlink)
    rc = main(
        [
            "framework",
            "validate",
            "--profile",
            "qualification",
            "--source-revision",
            SOURCE_REVISION,
            "--configuration-sha256",
            CONFIGURATION_SHA256,
            "--project",
            str(project),
            "--report-json",
            str(output),
        ]
    )

    assert rc == 2
    assert not output.exists()
    assert temporary.read_bytes() == b""
