"""Sphinx configuration for an ASIL D SEooC C library qualification project.

This template follows ISO 26262-6:2018 for software-level product development
targeting ASIL D. It includes sphinx-needs, conditional PlantUML, reproducible
JSON output, and need type definitions for software SEooC qualification.

For content-authoring guidance, load the `iso26262-part6-software` skill.
"""

from __future__ import annotations

import os
import shutil
from importlib.metadata import version as _package_version
from pathlib import Path

project = "ASIL D SEooC Qualification (C)"
author = "OSQAr"
copyright = "OSQAr Contributors"

extensions = [
    "sphinx_needs",
]

# PlantUML is only loaded when diagrams are not explicitly disabled.
_NO_DIAGRAMS = os.environ.get("OSQAR_NO_DIAGRAMS", "").lower() in ("1", "true")
if not _NO_DIAGRAMS:
    extensions.append("sphinxcontrib.plantuml")

try:
    import sphinxcontrib.test_reports  # noqa: F401
except ModuleNotFoundError:
    pass
else:
    extensions.append("sphinxcontrib.test_reports")

html_theme = os.environ.get("OSQAR_SPHINX_THEME", "furo")
html_static_path = ["_static"]
html_css_files = ["custom.css", "furo-fixes.css"]
html_js_files = ["figure-zoom.js"]

exclude_patterns = [
    "_build",
    "build",
    ".venv",
    "__pycache__",
    "bazel-*",
]

needs_id_regex = "^[A-Z0-9_]{3,}"
needs_css = "modern.css"
needs_build_json = True
needs_reproducible_json = True

# Need types for software SEooC qualification targeting ASIL D.
# Includes REQ_SSR_, ARCH_, VER_, IMPL_, LM_, SC_, STDCLAIM_, and EVID_ prefixes.
needs_types = [
    dict(directive="need", title="Requirement", prefix="REQ_", color="#BFD8D2", style="node"),
    dict(directive="arch", title="Architecture", prefix="ARCH_", color="#FEDCD2", style="node"),
    dict(directive="ver", title="Verification", prefix="VER_", color="#DFCCF1", style="node"),
    dict(directive="impl", title="Implementation", prefix="IMPL_", color="#DCB239", style="node"),
    dict(directive="lm", title="Lifecycle", prefix="LM_", color="#B3C2F2", style="node"),
    dict(directive="sc", title="Safety Case", prefix="SC_", color="#C0E8D5", style="node"),
    dict(directive="stdclaim", title="Standards Claim", prefix="STDCLAIM_", color="#F4D06F", style="node"),
    dict(directive="evid", title="Evidence", prefix="EVID_", color="#A8D5BA", style="node"),
]

_needs_claim_fields = [
    "standards_catalog",
    "standards_refs",
    "project_interpretation",
    "applicability",
]

_needs_claim_links = [
    {
        "option": "collapsed",
        "incoming": "collapses to",
        "outgoing": "collapses",
    },
    {
        "option": "realized_by",
        "incoming": "realizes",
        "outgoing": "is realized by",
    },
    {
        "option": "verified_by",
        "incoming": "verifies",
        "outgoing": "is verified by",
    },
    {
        "option": "evidenced_by",
        "incoming": "evidences",
        "outgoing": "is evidenced by",
    },
]

# Sphinx-Needs 8 replaced the legacy list-based configuration with mappings.
# Keep both supported dependency generations warning-free because documentation
# builds treat warnings as errors.
_sphinx_needs_major = int(_package_version("sphinx-needs").split(".", 1)[0])
if _sphinx_needs_major >= 8:
    needs_fields = {
        field: {"schema": {"type": "string"}} for field in _needs_claim_fields
    }
    needs_links = {
        link["option"]: {
            "incoming": link["incoming"],
            "outgoing": link["outgoing"],
        }
        for link in _needs_claim_links
    }
else:
    needs_extra_options = _needs_claim_fields
    needs_extra_links = _needs_claim_links


def _ensure_file(path: Path, content: str) -> None:
    if path.exists():
        return
    path.write_text(content, encoding="utf-8")


_ensure_file(
    Path(__file__).parent / "test_results.xml",
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<testsuite name="asil_d_tests" tests="0" failures="0" errors="0" skipped="0" time="0" />\n',
)

_ensure_file(
    Path(__file__).parent / "coverage_report.txt",
    "Code coverage report not yet generated. Run: ./build-and-test.sh coverage\n",
)

_ensure_file(
    Path(__file__).parent / "complexity_report.txt",
    "Complexity report not yet generated. Run: ./build-and-test.sh complexity\n",
)

_ensure_file(
    Path(__file__).parent / "cppcheck_report.txt",
    "Static analysis report not yet generated. Run: ./build-and-test.sh static-analysis\n",
)

_ensure_file(
    Path(__file__).parent / "valgrind_report.txt",
    "Valgrind report not yet generated. Run: ./build-and-test.sh valgrind\n",
)


if not _NO_DIAGRAMS:
    plantuml_output_format = "svg"

    env_jar = os.environ.get("PLANTUML_JAR")
    if env_jar and Path(env_jar).is_file():
        plantuml = f'java -jar "{env_jar}"'
    elif shutil.which("plantuml"):
        plantuml = "plantuml"
    elif shutil.which("java"):
        for jar_path in (
            "/opt/plantuml/plantuml.jar",
            "/usr/share/plantuml/plantuml.jar",
        ):
            if Path(jar_path).is_file():
                plantuml = f'java -jar "{jar_path}"'
                break
        else:
            plantuml = "plantuml"
    else:
        plantuml = "plantuml"
