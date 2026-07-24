from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tools import osqar_cli


@pytest.mark.parametrize(
    ("template", "language", "language_file"),
    [
        ("asil_example_c", "c", "CMakeLists.txt"),
        ("asil_example_rust", "rust", "Cargo.toml"),
    ],
)
def test_new_creates_explicit_asil_target_examples(
    tmp_path: Path, template: str, language: str, language_file: str
) -> None:
    destination = tmp_path / template

    assert (
        osqar_cli.main(
            [
                "new",
                "--language",
                language,
                "--name",
                template,
                "--destination",
                str(destination),
                "--template",
                template,
                "--no-diagrams",
            ]
        )
        == 0
    )

    assert (destination / language_file).is_file()
    assert (destination / "00_standards_claims.rst").is_file()
    assert (destination / "osqar_project.json").is_file()


@pytest.mark.parametrize(
    ("template", "language"),
    [("asil_example_c", "rust"), ("asil_example_rust", "c")],
)
def test_new_rejects_asil_example_language_mismatch_without_creating_project(
    tmp_path: Path, template: str, language: str
) -> None:
    destination = tmp_path / "rejected"
    destination.mkdir()
    sentinel = destination / "sentinel.txt"
    sentinel.write_bytes(b"preserve me")

    assert (
        osqar_cli.main(
            [
                "new",
                "--language",
                language,
                "--name",
                "rejected",
                "--destination",
                str(destination),
                "--template",
                template,
                "--force",
            ]
        )
        == 2
    )
    assert sentinel.read_bytes() == b"preserve me"


def test_c_example_executes_documented_default_compiler_selection(tmp_path: Path) -> None:
    destination = tmp_path / "c-example"
    assert (
        osqar_cli.main(
            [
                "new",
                "--language",
                "c",
                "--name",
                "c-example",
                "--destination",
                str(destination),
                "--template",
                "asil_example_c",
                "--no-diagrams",
            ]
        )
        == 0
    )

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    compiler_log = tmp_path / "cmake-arguments.txt"
    fake_cmake = fake_bin / "cmake"
    fake_cmake.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$COMPILER_LOG\"\n",
        encoding="utf-8",
    )
    fake_cmake.chmod(0o755)
    fake_ctest = fake_bin / "ctest"
    fake_ctest.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_ctest.chmod(0o755)

    environment = os.environ.copy()
    environment.pop("CC", None)
    environment["PATH"] = f"{fake_bin}{os.pathsep}{environment['PATH']}"
    environment["COMPILER_LOG"] = str(compiler_log)
    completed = subprocess.run(
        [str(destination / "build-and-test.sh"), "test"],
        cwd=destination,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "-DCMAKE_C_COMPILER=cc" in compiler_log.read_text(encoding="utf-8")


def test_new_help_exposes_only_current_asil_examples() -> None:
    parser = osqar_cli.build_parser()
    new_parser = parser._subparsers._group_actions[0].choices["new"]
    template_action = next(
        action for action in new_parser._actions if action.dest == "template"
    )

    assert tuple(template_action.choices) == (
        "basic",
        "example",
        "asil_example_c",
        "asil_example_rust",
    )
    assert "asil-d_c" not in new_parser.format_help()
