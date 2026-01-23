# conf.py
# -- Project information -----------------------------------------------------
project = 'OSQAr'
copyright = '2025, OSQAr Contributors'
author = 'OSQAr Team'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx_needs',              # The core traceability extension
    'sphinxcontrib.plantuml',    # PlantUML integration
    'sphinx_press_theme',        # The requested theme
]

# -- Theme Configuration -----------------------------------------------------
html_theme = 'press'

# -- PlantUML Configuration --------------------------------------------------
# Ensure you have the plantuml.jar available or use a remote server.
# For local JAR:
# plantuml = 'java -jar /path/to/plantuml.jar'

# For a simpler start, you can often use the PlantUML web service (for public docs):
# plantuml_output_format = 'svg'

# -- Sphinx-Needs Configuration (Basic) --------------------------------------
needs_id_regex = '^[A-Z0-9_]{3,}'  # Enforce structured IDs (e.g., REQ_001)
needs_css = "modern.css"           # Use modern styling for need objects