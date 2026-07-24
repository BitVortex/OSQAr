import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_staging_is_excluded_from_source_checks() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"--ignore=_dist"' in pyproject

    sphinx_config = runpy.run_path(str(ROOT / "conf.py"))
    assert "_dist/**" in sphinx_config["exclude_patterns"]


def test_release_version_gate_accepts_matching_tag_and_rejects_mismatch() -> None:
    script = ROOT / "tools" / "check_release_version.py"

    matching = subprocess.run(
        [sys.executable, str(script), "--tag", "v0.10.1"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert matching.returncode == 0, matching.stderr

    mismatch = subprocess.run(
        [sys.executable, str(script), "--tag", "v9.9.9"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert mismatch.returncode != 0
    assert "does not match package version" in mismatch.stderr


def test_release_publish_jobs_depend_on_version_gate() -> None:
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch" not in workflow
    assert "  release-metadata:\n" in workflow
    assert "  pypi-publish:\n    needs:\n      - release-metadata\n      - release-inventory\n" in workflow
    assert "  framework-bundle:\n    needs: release-metadata\n" in workflow
    assert "  bazel-example-shipment:\n    needs: release-metadata\n" in workflow
    assert "      - release-metadata\n" in workflow


def test_installed_wheel_ci_stages_release_hygiene_inputs() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "cp index.rst pyproject.toml conf.py /tmp/osqar-installed-suite/" in workflow
    assert (
        "cp .github/workflows/ci.yml .github/workflows/release.yml "
        "/tmp/osqar-installed-suite/.github/workflows/"
    ) in workflow


def test_active_documentation_avoids_overstated_qualification_claims() -> None:
    paths = [ROOT / "README.md", ROOT / "docs", ROOT / "tools" / "osqar_cmd_gsn.py"]
    texts: list[str] = []
    for path in paths:
        if path.is_dir():
            texts.extend(
                item.read_text(encoding="utf-8") for item in path.rglob("*.rst")
            )
        elif path.is_file():
            texts.append(path.read_text(encoding="utf-8"))
    active_text = "\n".join(texts)
    assert "OSQAr-qualified" not in active_text
    assert "formally correct GSN" not in active_text


def test_installed_wheel_ci_deselects_source_checkout_tests() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '-m "not source_checkout"' in workflow
    assert '"source_checkout: requires a complete repository checkout"' in pyproject
