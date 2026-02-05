"""Sphinx configuration for a minimal OSQAr C++ project template."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

project = "OSQAr: Project (C++)"
author = "OSQAr"

extensions = [
    "sphinx_needs",
    "sphinxcontrib.plantuml",
]

try:
    import sphinxcontrib.test_reports  # noqa: F401
except ModuleNotFoundError:
    pass
else:
    extensions.append("sphinxcontrib.test_reports")

html_theme = os.environ.get("OSQAR_SPHINX_THEME", "furo")
html_static_path = ["_static"]
html_css_files = ["custom.css"]

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


def _ensure_file(path: Path, content: str) -> None:
    if path.exists():
        return
    path.write_text(content, encoding="utf-8")


_ensure_file(
    Path(__file__).parent / "test_results.xml",
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<testsuite name="tests" tests="0" failures="0" errors="0" skipped="0" time="0" />\n',
)

_ensure_file(
    Path(__file__).parent / "coverage_report.txt",
    "Code coverage report not generated in this build.\n",
)

_ensure_file(
    Path(__file__).parent / "complexity_report.txt",
    "Complexity report not generated in this build.\n",
)

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
        "/usr/local/opt/plantuml/libexec/plantuml.jar",
    ):
        try:
            subprocess.run(
                ["java", "-jar", jar_path, "-version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
            plantuml = f'java -jar "{jar_path}"'
            break
        except Exception:
            continue
    else:
        plantuml_server = "https://www.plantuml.com/plantuml"
else:
    plantuml_server = "https://www.plantuml.com/plantuml"
