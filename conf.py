# conf.py
# -- Project information -----------------------------------------------------
project = 'OSQAr'
copyright = '2025, OSQAr Contributors'
author = 'OSQAr Team'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx_needs',              # The core traceability extension
    'sphinxcontrib.plantuml',    # PlantUML integration
]

# -- Theme Configuration -----------------------------------------------------
# Default to a modern theme, but keep it overridable for compatibility.
# Furo includes built-in light/dark mode support.
# Set `OSQAR_SPHINX_THEME=alabaster` to fall back to the built-in theme.
import os

html_theme = os.environ.get('OSQAR_SPHINX_THEME', 'furo')

# -- PlantUML Configuration --------------------------------------------------
# Ensure you have the plantuml.jar available or use a remote server.
# For local JAR:
# plantuml = 'java -jar /path/to/plantuml.jar'

# For a simpler start, you can often use the PlantUML web service (for public docs):
# plantuml_output_format = 'svg'

# -- Sphinx-Needs Configuration (Basic) --------------------------------------
needs_id_regex = '^[A-Z0-9_]{3,}'  # Enforce structured IDs (e.g., REQ_001)
needs_css = "modern.css"           # Use modern styling for need objects