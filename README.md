[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# OSQAr

Open Safety Qualification Architecture (OSQAr) — a Sphinx + sphinx-needs boilerplate for building **auditable safety/compliance documentation** with:

- requirements + traceability (sphinx-needs)
- architecture diagrams (PlantUML)
- verification planning and traceability matrices

For license terms see the `LICENSE` file (Apache License 2.0).

## Documentation (GitHub Pages)

- Framework documentation (landing page): https://bitvortex.github.io/OSQAr/
- Reference example project: https://bitvortex.github.io/OSQAr/example/

GitHub Pages is built automatically on pushes to `main` via `.github/workflows/pages-deploy.yml`.

The docs default to the `furo` theme (with built-in light/dark mode). To force a fallback theme, set `OSQAR_SPHINX_THEME=alabaster`.

## Repository structure

- Framework documentation (general guides):
	- `index.rst` (framework landing page)
	- `docs/` (guides such as integrator/supplier usage)
	- `conf.py` (root Sphinx configuration; intentionally excludes `examples/**`)

- Reference implementation (example project):
	- `examples/hello_world/` (end-to-end reference project demonstrating requirements → architecture → verification → tests)
	- `examples/hello_world/conf.py` (example-specific Sphinx config, including PlantUML setup)
	- `examples/hello_world/build-and-test.sh` (scripted workflow: test → docs → traceability)

- Styling:
	- `_static/` (root static assets for framework docs)
	- `examples/hello_world/_static/` (example-specific tweaks)

## Build locally

### Framework documentation (repo root)

```bash
poetry install
poetry run sphinx-build -b html . _build/html
open _build/html/index.html
```

### Example project documentation (published under `/example/`)

```bash
poetry install
poetry run sphinx-build -b html examples/hello_world _build/html/example
open _build/html/example/index.html
```

### Optional environment variables

- `OSQAR_SPHINX_THEME`: override theme (e.g., `furo`, `alabaster`)
- `PLANTUML_JAR`: point to a local `plantuml.jar` for offline PlantUML rendering

## Start here

If you are new to the repository:

1. Open the framework docs: https://bitvortex.github.io/OSQAr/
2. Then explore the example project: https://bitvortex.github.io/OSQAr/example/
3. If you want to copy a proven structure, start from `examples/hello_world/` and replace its requirements/diagrams/tests with your system’s artifacts.

## Legacy note

The file `docs/BOILERPLATE_USAGE.md` is a GitHub-readable overview. The authoritative framework documentation lives in `index.rst` and `docs/*.rst` and is what gets published to GitHub Pages.

---

### Build the example with the example’s original output path (legacy command)

Some older instructions build into `examples/hello_world/_build/html/example`. This still works, but the recommended approach is to build the example under the root output directory (`_build/html/example`) so it matches how GitHub Pages publishes the site.

```bash
poetry install
poetry run sphinx-build -b html examples/hello_world examples/hello_world/_build/html/example
open examples/hello_world/_build/html/example/index.html
```
