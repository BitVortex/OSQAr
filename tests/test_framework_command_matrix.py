from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest
import tools

from tools import osqar_cli_util, osqar_cmd_sign
from tools.framework_test_report import FrameworkReportError, validate_junit_report
from tools.osqar_cli import main
from tools.traceability_check import cli as traceability_cli


ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = Path(tools.__file__).resolve().parent

# Every command that generates, transforms, signs, verifies, packages, or reports
# assurance-relevant artifacts must name at least one direct negative-path test.
COMMAND_TEST_MATRIX = {
    "osqar_cmd_baseline": ("test_command_negative_paths.py", "test_baseline_diff_rejects_non_object_manifest"),
    "osqar_cmd_checksum": ("test_checksum_failures.py", "test_checksum_mismatch_and_missing_return_failure_with_report"),
    "osqar_cmd_code_trace": ("test_framework_command_matrix.py", "test_commands_reject_missing_or_malformed_inputs"),
    "osqar_cmd_doctor": ("test_framework_command_matrix.py", "test_commands_reject_missing_or_malformed_inputs"),
    "osqar_cmd_framework": ("test_framework_command_matrix.py", "test_commands_reject_missing_or_malformed_inputs"),
    "osqar_cmd_gsn": ("test_framework_command_matrix.py", "test_commands_reject_missing_or_malformed_inputs"),
    "osqar_cmd_impact": ("test_framework_command_matrix.py", "test_commands_reject_missing_or_malformed_inputs"),
    "osqar_cmd_new": ("test_framework_command_matrix.py", "test_commands_reject_missing_or_malformed_inputs"),
    "osqar_cmd_release_manifest": ("test_release_manifest_cli.py", "test_verify_rejects_report_inside_shipment_without_stale_pass"),
    "osqar_cmd_setup": ("test_framework_command_matrix.py", "test_commands_reject_missing_or_malformed_inputs"),
    "osqar_cmd_shipment": ("test_framework_command_matrix.py", "test_commands_reject_missing_or_malformed_inputs"),
    "osqar_cmd_sign": ("test_command_negative_paths.py", "test_sign_create_rejects_success_without_signature"),
    "osqar_cmd_traceability": ("test_framework_command_matrix.py", "test_traceability_rejects_dead_link"),
    "osqar_cmd_workspace": ("test_command_negative_paths.py", "test_workspace_combine_rejects_malformed_project_needs"),
}

# This command only opens already-generated documentation. It does not generate,
# transform, sign, verify, package, or report evidence and is outside #23's
# safety-relevant command boundary.
EXCLUDED_COMMANDS = {"osqar_cmd_open_docs": "documentation launcher only"}


def _test_function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_safety_relevant_command_module_matrix_is_complete() -> None:
    discovered = {path.stem for path in TOOLS_ROOT.glob("osqar_cmd_*.py")}
    assert discovered == set(COMMAND_TEST_MATRIX) | set(EXCLUDED_COMMANDS)
    assert EXCLUDED_COMMANDS == {"osqar_cmd_open_docs": "documentation launcher only"}

    for module, (test_file, test_name) in COMMAND_TEST_MATRIX.items():
        assert (TOOLS_ROOT / f"{module}.py").is_file()
        assert test_name in _test_function_names(ROOT / "tests" / test_file)


def test_commands_reject_missing_or_malformed_inputs(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "missing"
    bad_json = tmp_path / "malformed.json"
    bad_json.write_text("{ malformed", encoding="utf-8")
    existing_destination = tmp_path / "already-exists"
    existing_destination.mkdir()

    cases = [
        (["doctor", "--project", str(missing)], "project directory not found"),
        (["setup", str(missing.with_suffix(".zip")), "--output", str(tmp_path / "setup")], "zip archive not found"),
        (["new", "--language", "python", "--name", "fixture", "--destination", str(existing_destination)], "destination already exists"),
        (["impact", str(bad_json), "--need-id", "REQ_1"], "failed to read"),
        (["code-trace", "--root", str(missing), "--needs-json", str(bad_json)], "root not found"),
        (["gsn", "generate", str(bad_json), "--output", str(tmp_path / "gsn.puml")], "failed to read"),
        (["framework", "bundle", "--version", "v1", "--docs-dir", str(missing), "--output-dir", str(tmp_path / "bundle")], "docs dir not found"),
        (["shipment", "prepare", "--project", str(missing)], "not a shipment project directory"),
        (["shipment", "run-tests", "--project", str(missing)], "no test command configured"),
        (["shipment", "run-build", "--project", str(missing)], "project directory not found"),
        (["shipment", "package", "--shipment", str(missing), "--output", str(tmp_path / "shipment.zip")], "shipment directory not found"),
    ]

    for argv, diagnostic in cases:
        assert main(argv) != 0, argv
        captured = capsys.readouterr()
        assert diagnostic in (captured.out + captured.err).lower(), argv

    assert not (tmp_path / "gsn.puml").exists()
    assert not (tmp_path / "bundle").exists()
    assert not (tmp_path / "shipment.zip").exists()


def test_traceability_rejects_dead_link(tmp_path: Path, capsys) -> None:
    needs = tmp_path / "needs.json"
    needs.write_text(
        json.dumps({"needs": [{"id": "REQ_1", "links": ["ARCH_MISSING"]}]}),
        encoding="utf-8",
    )

    assert traceability_cli([str(needs)]) == 1
    assert "outgoing link to unknown need id" in capsys.readouterr().out.lower()


def test_real_crashed_executable_cannot_supply_omitted_report(tmp_path: Path) -> None:
    crash = tmp_path / "crash.py"
    report = tmp_path / "omitted-junit.xml"
    crash.write_text("raise SystemExit(17)\n", encoding="utf-8")

    assert osqar_cli_util.run([sys.executable, str(crash)], cwd=tmp_path) == 17
    assert not report.exists()
    with pytest.raises(FrameworkReportError, match="not found"):
        validate_junit_report(report)


def test_sign_verify_propagates_invalid_signature_tool_result(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    manifest = tmp_path / "SHA256SUMS"
    signature = tmp_path / "SHA256SUMS.sig"
    manifest.write_text("payload", encoding="utf-8")
    signature.write_text("invalid signature", encoding="utf-8")
    monkeypatch.setattr(osqar_cmd_sign, "_find_gpg", lambda: "fake-gpg")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 1, "", "BAD signature"
        ),
    )

    assert (
        main(
            [
                "sign",
                "verify",
                "--manifest",
                str(manifest),
                "--signature",
                str(signature),
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "bad signature" in (captured.out + captured.err).lower()
