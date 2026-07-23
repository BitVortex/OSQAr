from __future__ import annotations

from pathlib import Path

import yaml


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml"


def _test_steps() -> list[dict[str, object]]:
    workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    return workflow["jobs"]["test"]["steps"]


def _step(name: str) -> dict[str, object]:
    return next(step for step in _test_steps() if step.get("name") == name)


def test_source_framework_evidence_command_is_fail_closed_and_published_per_lane() -> None:
    run = str(_step("Framework regression and fault-injection tests")["run"])
    assert "set -euo pipefail" in run
    assert "python -m pytest -q tests" in run
    assert "--junitxml=framework-test-results.xml" in run
    assert "--cov-report=xml:framework-coverage.xml" in run
    assert "python -m tools.framework_test_report" in run
    assert "--json-report framework-test-validation.json" in run
    assert "|| true" not in run

    upload = _step("Upload source framework evidence")
    assert upload["if"] == "always()"
    assert upload["uses"] == "actions/upload-artifact@v4"
    with_block = upload["with"]
    assert with_block["name"] == "framework-evidence-source-python-${{ matrix.python-version }}"
    assert set(str(with_block["path"]).splitlines()) == {
        "framework-test-results.xml",
        "framework-test-validation.json",
        "framework-coverage.xml",
    }


def test_workflow_contract_exercises_skipped_and_zero_reports_without_masking_validator() -> None:
    run = str(_step("Prove framework evidence validator fails closed")["run"])
    assert "set -euo pipefail" in run
    assert "seeded-skipped.xml" in run
    assert "seeded-zero.xml" in run
    assert run.count("python -m tools.framework_test_report") == 2
    assert run.count("if poetry run python -m tools.framework_test_report") == 2
    assert "|| true" not in run


def test_installed_wheel_lane_emits_validated_evidence_and_proves_isolation() -> None:
    run = str(_step("Build and test installed wheel")["run"])
    assert "set -euo pipefail" in run
    assert "--junitxml=$GITHUB_WORKSPACE/installed-wheel-test-results.xml" in run
    assert "--cov-report=xml:$GITHUB_WORKSPACE/installed-wheel-coverage.xml" in run
    assert "/tmp/osqar-wheel/bin/python -m tools.framework_test_report" in run
    assert "--json-report $GITHUB_WORKSPACE/installed-wheel-test-validation.json" in run
    assert "import tools" in run
    assert "import osqar_data" in run
    assert "importlib.resources.files(osqar_data)" in run
    assert "source_checkout" in run
    assert "cp -R tests docs skills tools" in run
    assert "cp -R osqar_data/templates" in run
    assert "cp index.rst pyproject.toml" in run
    assert "rm /tmp/osqar-installed-suite/tools/__init__.py" in run
    assert "|| true" not in run

    upload = _step("Upload installed-wheel framework evidence")
    assert upload["if"] == "always()"
    assert upload["uses"] == "actions/upload-artifact@v4"
    with_block = upload["with"]
    assert with_block["name"] == "framework-evidence-wheel-python-${{ matrix.python-version }}"
    assert set(str(with_block["path"]).splitlines()) == {
        "installed-wheel-test-results.xml",
        "installed-wheel-test-validation.json",
        "installed-wheel-coverage.xml",
    }


def test_mandatory_gsn_commands_and_status_checks_do_not_suppress_failures() -> None:
    run = str(_step("Exercise new commands (impact, CSV, XLSX, workspace combine, gsn)")["run"])
    assert "|| true" not in run
    assert "test -s _build/gsn_safety_case.puml" in run
    assert "grep -q '@startuml' _build/gsn_safety_case.puml" in run
    assert "grep -q '@enduml' _build/gsn_safety_case.puml" in run
    assert "test -s _build/gsn_safety_case.yaml" in run
