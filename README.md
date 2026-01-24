[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# OSQAr

Open Safety Qualification Architecture (OSQAr) — a Sphinx + sphinx-needs
boilerplate for requirements traceability, architecture diagrams, and
test traceability suitable for safety-related documentation and examples.

For license terms see the `LICENSE` file (Apache License 2.0).

The [example](https://bitvortex.github.io/OSQAr/example/) is built and deployed automatically on pushes to `main` (via `.github/workflows/pages-deploy.yml`) from the sources in the `examples/hello_world` directory. It shall serve as a reference on how a toolchain setup could look like.

The docs default to the `furo` theme (with built-in light/dark mode). To force a fallback theme, set `OSQAR_SPHINX_THEME=alabaster`.

## How to use this boilerplate

- Framework documentation (general guides): `index.rst` + `docs/*.rst`
- Reference implementation (example project): `examples/hello_world/` (published to GitHub Pages)

## Build the framework documentation (repo root)

```bash
poetry install
poetry run sphinx-build -b html . _build/html
open _build/html/index.html
```

## Build the example application documentation

```bash
# from the repository root
poetry install
poetry run sphinx-build -b html examples/hello_world examples/hello_world/_build/html/example
open examples/hello_world/_build/html/example/index.html
```

To view the example locally:

```bash
# from the repository root
poetry install

# Optional theme override
export OSQAR_SPHINX_THEME=furo

# If you want local PlantUML rendering via a jar, point Sphinx at it.
# (CI downloads a jar and sets PLANTUML_JAR automatically.)
# export PLANTUML_JAR=/absolute/path/to/plantuml.jar

poetry run sphinx-build -b html examples/hello_world examples/hello_world/_build/html/example
open examples/hello_world/_build/html/example/index.html
```
