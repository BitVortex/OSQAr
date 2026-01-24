"""Sphinx configuration for OSQAr framework documentation (repo root)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


# -- Project information -----------------------------------------------------
project = 'OSQAr'
copyright = '2025, OSQAr Contributors'
author = 'OSQAr Team'


# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx_needs',
    'sphinxcontrib.plantuml',
]

# The root documentation is framework documentation.
# Example projects (under examples/*) are built separately and should not be
# treated as root Sphinx sources.
exclude_patterns = [
    '_build',
    'examples/**',
]


# -- Theme configuration -----------------------------------------------------
# Default to a modern theme, but keep it overridable for compatibility.
# Furo includes built-in light/dark mode support.
html_theme = os.environ.get('OSQAR_SPHINX_THEME', 'furo')

html_static_path = ['_static']
# Only inject our fallback CSS when using a theme without built-in dark mode.
# For furo, this caused readability issues by overriding theme colors.
html_css_files = ['custom.css'] if html_theme != 'furo' else []


# -- sphinx-needs ------------------------------------------------------------
needs_id_regex = '^[A-Z0-9_]{3,}'
needs_css = 'modern.css'


# -- PlantUML ----------------------------------------------------------------
plantuml_output_format = 'svg'

env_jar = os.environ.get('PLANTUML_JAR')
if env_jar and Path(env_jar).is_file():
    plantuml = f'java -jar "{env_jar}"'
    print(f"✓ Using PLANTUML JAR from environment: {env_jar}")
elif env_jar:
    print(f"! PLANTUML_JAR is set but not found at: {env_jar}; falling back")

if 'plantuml' not in globals() and 'plantuml_server' not in globals():
    if shutil.which('plantuml'):
        plantuml = 'plantuml'
        print("✓ Using system 'plantuml' command")
    elif shutil.which('java'):
        jar_paths = [
            '/opt/plantuml/plantuml.jar',
            '/usr/share/plantuml/plantuml.jar',
            '/usr/local/opt/plantuml/libexec/plantuml.jar',
        ]
        for jar_path in jar_paths:
            try:
                subprocess.run(
                    ['java', '-jar', jar_path, '-version'],
                    capture_output=True,
                    check=True,
                    timeout=5,
                )
                plantuml = f'java -jar "{jar_path}"'
                print(f"✓ Using PlantUML JAR: {jar_path}")
                break
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                continue
        else:
            plantuml_server = 'https://www.plantuml.com/plantuml'
            print('! PlantUML JAR not found; using web service')
    else:
        plantuml_server = 'https://www.plantuml.com/plantuml'
        print('! PlantUML and Java not found; using web service (requires internet)')