"""Sphinx configuration for OSQAr framework documentation (repo root)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path


# -- Project information -----------------------------------------------------
project = "OSQAr"
copyright = "2025, OSQAr Contributors"
author = "OSQAr Team"


def _read_project_version() -> str | None:
    """Extract OSQAr version from pyproject.toml without extra dependencies.

    Prefers the PEP 621 ``[project]`` table. Falls back to legacy
    ``[tool.poetry]`` for compatibility.

    We intentionally avoid tomllib/tomli to keep compatibility with older Python
    versions used in CI.
    """

    pyproject = Path(__file__).with_name("pyproject.toml")
    if not pyproject.is_file():
        return None

    text = pyproject.read_text(encoding="utf-8")

    def find_version_in_section(section_name: str) -> str | None:
        start = text.find(section_name)
        if start == -1:
            return None
        rest = text[start + len(section_name) :]
        next_section = rest.find("\n[")
        section = rest if next_section == -1 else rest[:next_section]
        m = re.search(r'^\s*version\s*=\s*"([^"]+)"\s*$', section, flags=re.MULTILINE)
        return m.group(1) if m else None

    return find_version_in_section("[project]") or find_version_in_section("[tool.poetry]")


# Sphinx version string (shown by themes that display it).
release = _read_project_version() or "0.0.0"
version = ".".join(release.split(".")[:2])


# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx_needs",
    "sphinxcontrib.plantuml",
]

# The root documentation is framework documentation.
# Example projects (under examples/*) are built separately and should not be
# treated as root Sphinx sources.
exclude_patterns = [
    "_build",
    # Local Poetry/virtualenv (otherwise Sphinx may index site-packages .rst files).
    ".venv",
    ".venv/**",
    # The example projects are built separately.
    "examples/*_hello_world/**",
    # Shared example chapter sources are included by example projects.
    "examples/tsim_docs/**",
    # Project scaffolding templates are Sphinx projects on their own and are
    # not part of the root framework documentation.
    "templates/**",
]


# -- Theme configuration -----------------------------------------------------
# Default to a modern theme, but keep it overridable for compatibility.
# Furo includes built-in light/dark mode support.
html_theme = os.environ.get("OSQAR_SPHINX_THEME", "furo")

html_static_path = ["_static"]

# Keep indices tidy: this is not an API reference.
html_use_index = False
html_domain_indices = False
html_use_modindex = False

# Styling:
# - `custom.css` provides a generic dark-mode fallback for themes without built-in dark mode.
# - `furo-fixes.css` contains small, safe tweaks for PlantUML + sphinx-needs that should
#   apply even when using furo.
if html_theme == "furo":
    html_css_files = ["furo-fixes.css"]
else:
    html_css_files = ["custom.css", "furo-fixes.css"]


# -- sphinx-needs ------------------------------------------------------------
needs_id_regex = "^[A-Z0-9_]{3,}"
needs_css = "modern.css"

# Export a reproducible needs.json alongside the normal HTML build.
# This is used by CI for traceability checks and for producing audit-friendly artifacts.
needs_build_json = True
needs_reproducible_json = True


# -- PlantUML ----------------------------------------------------------------
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
            plantuml_server = "https://www.plantuml.com/plantuml"
            print("! PlantUML JAR not found; using web service")
    else:
        plantuml_server = "https://www.plantuml.com/plantuml"
        print("! PlantUML and Java not found; using web service (requires internet)")
