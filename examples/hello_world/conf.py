# conf.py for OSQAr Hello World Example
# This is a minimal conf.py that extends the root OSQAr configuration

import sys
from pathlib import Path

# Add parent directories to path to inherit settings
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

project = 'OSQAr Hello World: Temperature Monitor'
copyright = '2025, OSQAr Contributors'
author = 'OSQAr Team'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx_needs',              # The core traceability extension
    'sphinxcontrib.plantuml',    # PlantUML integration for architecture diagrams
]

html_theme = 'alabaster'  # Use built-in theme for better compatibility
# -- Sphinx-Needs Configuration (Basic) -----------------------------------
# -- Sphinx-Needs Configuration (Basic) -----------------------------------
needs_id_regex = '^[A-Z0-9_]{3,}'
needs_css = "modern.css"

# -- Test Results Configuration -------------------------------------------
# Path to JUnit XML test results (can be processed by CI/CD for compliance)
test_results_file = 'test_results.xml'

# -- PlantUML Configuration ---------------------------------------------------
import shutil
import subprocess

plantuml_output_format = 'svg'

# Allow CI to provide a PLANTUML_JAR path via environment for local rendering
import os
env_jar = os.environ.get('PLANTUML_JAR')
if env_jar:
    plantuml = f'java -jar {env_jar}'
    print(f"✓ Using PLANTUML JAR from environment: {env_jar}")
else:
    # Strategy 1: Try to use installed plantuml command
    if shutil.which('plantuml'):
        plantuml = 'plantuml'
        print("✓ Using system 'plantuml' command")
    # Strategy 2: Try to use Java + JAR file if available
    elif shutil.which('java'):
        try:
            jar_paths = [
                '/opt/plantuml/plantuml.jar',
                '/usr/share/plantuml/plantuml.jar',
                '/usr/local/opt/plantuml/libexec/plantuml.jar',
            ]
            for jar_path in jar_paths:
                try:
                    subprocess.run(['java', '-jar', jar_path, '-version'],
                                   capture_output=True, check=True, timeout=5)
                    plantuml = f'java -jar {jar_path}'
                    print(f"✓ Using PlantUML JAR: {jar_path}")
                    break
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                    continue
            else:
                # Java available but no JAR found, try web service
                print("! PlantUML JAR not found; attempting to use web service")
                plantuml_server = 'http://www.plantuml.com/plantuml'
        except Exception as e:
            print(f"✗ PlantUML configuration error: {e}")
            plantuml_server = 'http://www.plantuml.com/plantuml'
    else:
        # Last resort: web service (requires internet connection)
        print("! PlantUML and Java not found; using web service (requires internet)")
        plantuml_server = 'http://www.plantuml.com/plantuml'

# PlantUML output directory
plantuml_output_directory = '_diagrams'

# Create diagrams output directory if using local rendering
import os
if os.path.exists('diagrams'):
    os.makedirs(plantuml_output_directory, exist_ok=True)
