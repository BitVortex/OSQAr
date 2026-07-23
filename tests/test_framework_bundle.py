import shutil
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

from tools import osqar_cmd_framework
from tools.osqar_cmd_framework import cmd_framework_bundle


def test_framework_bundle_includes_runtime_package_resources(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.html").write_text("OSQAr docs\n", encoding="utf-8")

    output = tmp_path / "output"
    result = cmd_framework_bundle(
        Namespace(version="v0.10.0", docs_dir=docs, output_dir=output)
    )

    assert result == 0
    bundle = output / "osqar-framework-v0.10.0"
    for resource in (
        "osqar_data/__init__.py",
        "osqar_data/governance/tool-reliance-v1.json",
        "osqar_data/profiles/qualification.yaml",
        "osqar_data/standards/iso26262_reference_catalog.json",
        "osqar_data/templates/basic/shared/01_requirements.rst",
    ):
        assert (bundle / resource).is_file(), resource
    assert not (bundle / "templates").exists()


def test_installed_bundle_generates_runnable_launchers(
    tmp_path: Path, monkeypatch
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.html").write_text("OSQAr docs\n", encoding="utf-8")

    installed_module = tmp_path / "site-packages" / "tools" / "osqar_cmd_framework.py"
    shutil.copytree(Path(__file__).resolve().parents[1] / "tools", installed_module.parent)
    monkeypatch.setattr(osqar_cmd_framework, "__file__", str(installed_module))

    output = tmp_path / "output"
    result = cmd_framework_bundle(
        Namespace(version="v0.10.0", docs_dir=docs, output_dir=output)
    )

    assert result == 0
    bundle = output / "osqar-framework-v0.10.0"
    for launcher in ("osqar", "osqar.cmd", "osqar.ps1"):
        assert (bundle / launcher).is_file(), launcher
    assert not (bundle / "templates").exists()

    probe = subprocess.run(
        [str(bundle / "osqar"), "--help"],
        cwd=bundle,
        capture_output=True,
        text=True,
        check=False,
    )
    assert probe.returncode == 0, probe.stderr
    assert "OSQAr helper CLI" in probe.stdout


@pytest.mark.source_checkout
def test_release_workflow_bundle_uses_canonical_runtime_resources(
    tmp_path: Path,
) -> None:
    from ci.assemble_framework_bundle import assemble_bundle

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.html").write_text("OSQAr docs\n", encoding="utf-8")

    bundle = assemble_bundle(
        version="v0.10.0", docs_dir=docs, output_dir=tmp_path / "output"
    )

    for resource in (
        "osqar_data/__init__.py",
        "osqar_data/governance/tool-reliance-v1.json",
        "osqar_data/profiles/qualification.yaml",
        "osqar_data/standards/iso26262_reference_catalog.json",
        "osqar_data/templates/basic/shared/01_requirements.rst",
    ):
        assert (bundle / resource).is_file(), resource
    assert not (bundle / "templates").exists()
