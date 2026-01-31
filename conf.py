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
    # The example projects are built separately.
    'examples/*_hello_world/**',
    # Shared example chapter sources are included by example projects.
    'examples/tsim_docs/**',
]


# -- Theme configuration -----------------------------------------------------
# Default to a modern theme, but keep it overridable for compatibility.
# Furo includes built-in light/dark mode support.
html_theme = os.environ.get('OSQAR_SPHINX_THEME', 'furo')

html_static_path = ['_static']

# Keep indices tidy: this is not an API reference.
html_use_index = False
html_domain_indices = False
html_use_modindex = False

# Styling:
# - `custom.css` provides a generic dark-mode fallback for themes without built-in dark mode.
# - `furo-fixes.css` contains small, safe tweaks for PlantUML + sphinx-needs that should
#   apply even when using furo.
if html_theme == 'furo':
    html_css_files = ['furo-fixes.css']
else:
    html_css_files = ['custom.css', 'furo-fixes.css']


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