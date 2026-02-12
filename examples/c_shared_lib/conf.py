"""Sphinx configuration for the OSQAr shared C library example."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

project = "OSQAr: Shared C Library"
copyright = "2025, OSQAr Contributors"
author = "OSQAr Team"

extensions = [
    "sphinx_needs",
    "sphinxcontrib.plantuml",
    "sphinx.ext.ifconfig",
]

try:
    import sphinxcontrib.test_reports  # noqa: F401
except ModuleNotFoundError:
    print("! sphinx-test-reports not installed; test result import disabled")
else:
    extensions.append("sphinxcontrib.test_reports")

html_theme = os.environ.get("OSQAR_SPHINX_THEME", "furo")
html_static_path = ["_static"]
html_css_files = ["custom.css"]

html_use_index = False
html_domain_indices = False
html_use_modindex = False

exclude_patterns = [
    "_build",
    "build",
    ".venv",
    "__pycache__",
    "bazel-*",
    "bazel-bin",
    "bazel-out",
    "bazel-testlogs",
]

needs_id_regex = "^[A-Z0-9_]{3,}"
needs_css = "modern.css"
needs_build_json = True
needs_reproducible_json = True


def _ensure_test_results_xml() -> None:
    report_path = Path(__file__).parent / "test_results.xml"
    if report_path.exists():
        return
    report_path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<testsuite name="tests" tests="0" failures="0" errors="0" skipped="0" time="0" />\n',
        encoding="utf-8",
    )


def _ensure_coverage_report() -> None:
    report_path = Path(__file__).parent / "coverage_report.txt"
    if report_path.exists():
        return
    report_path.write_text(
        "Code coverage report not generated in this build.\n"
        "Run: OSQAR_COVERAGE=1 ./build-and-test.sh\n",
        encoding="utf-8",
    )


def _write_complexity_report() -> None:
    report_path = Path(__file__).parent / "complexity_report.txt"

    try:
        if shutil.which("lizard"):
            result = subprocess.run(
                ["lizard", "-C", "10", "src", "include", "tests"],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
            )
            report_path.write_text(
                result.stdout + (result.stderr or ""), encoding="utf-8"
            )
        else:
            report_path.write_text(
                "lizard is not available in this environment.\n"
                "Install with: poetry install (dev deps)\n",
                encoding="utf-8",
            )
    except Exception as exc:  # noqa: BLE001
        report_path.write_text(
            f"Failed to generate complexity report: {exc}\n", encoding="utf-8"
        )


_write_complexity_report()
_ensure_coverage_report()
_ensure_test_results_xml()

plantuml_output_format = "svg"

env_jar = os.environ.get("PLANTUML_JAR")
if env_jar and Path(env_jar).is_file():
    plantuml = f'java -jar "{env_jar}"'
    print(f"✓ Using PLANTUML JAR from environment: {env_jar}")
elif env_jar:
    print(f"! PLANTUML_JAR is set but not found at: {env_jar}; falling back")

if "plantuml" not in globals() and "plantuml_server" not in globals():
    if shutil.which("plantuml"):
        plantuml = "plantuml"
        print("✓ Using system 'plantuml' command")
    elif shutil.which("java"):
        jar_paths = [
            "/opt/plantuml/plantuml.jar",
            "/usr/share/plantuml/plantuml.jar",
            "/usr/local/opt/plantuml/libexec/plantuml.jar",
        ]
        for jar_path in jar_paths:
            try:
                subprocess.run(
                    ["java", "-jar", jar_path, "-version"],
                    capture_output=True,
                    check=True,
                    timeout=5,
                )
                plantuml = f'java -jar "{jar_path}"'
                print(f"✓ Using PlantUML JAR: {jar_path}")
                break
            except (
                subprocess.CalledProcessError,
                subprocess.TimeoutExpired,
                FileNotFoundError,
            ):
                continue
        else:
            print("! PlantUML JAR not found; using web service")
            plantuml_server = "https://www.plantuml.com/plantuml"
    else:
        print("! PlantUML and Java not found; using web service (requires internet)")
        plantuml_server = "https://www.plantuml.com/plantuml"

plantuml_output_directory = "_diagrams"
if Path("diagrams").exists():
    Path(plantuml_output_directory).mkdir(parents=True, exist_ok=True)
