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
# Use a built-in, well-supported theme for CI builds to avoid compatibility
# issues with third-party themes (the project previously used `press`).
# To restore `sphinx_press_theme`, add it back to `extensions` and set
# `html_theme = 'press'` after confirming compatibility with your Sphinx
# version (or upgrading the theme).
html_theme = 'alabaster'

# -- PlantUML Configuration --------------------------------------------------
# Ensure you have the plantuml.jar available or use a remote server.
# For local JAR:
# plantuml = 'java -jar /path/to/plantuml.jar'

# For a simpler start, you can often use the PlantUML web service (for public docs):
# plantuml_output_format = 'svg'

# -- Sphinx-Needs Configuration (Basic) --------------------------------------
needs_id_regex = '^[A-Z0-9_]{3,}'  # Enforce structured IDs (e.g., REQ_001)
needs_css = "modern.css"           # Use modern styling for need objects