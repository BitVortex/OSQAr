[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# OSQAr

Open Safety Qualification Architecture (OSQAr) — a Sphinx + sphinx-needs boilerplate for building **auditable safety/compliance documentation** with:

- requirements + traceability (sphinx-needs)
- architecture diagrams (PlantUML)
- verification planning and traceability matrices

For license terms see the `LICENSE` file (Apache License 2.0).

## Documentation (GitHub Pages)

- Framework documentation (landing page): https://bitvortex.github.io/OSQAr/

Published examples:

- Default example (C): https://bitvortex.github.io/OSQAr/example/
- Examples index: https://bitvortex.github.io/OSQAr/examples/
- C++ example: https://bitvortex.github.io/OSQAr/examples/cpp/
- Rust example: https://bitvortex.github.io/OSQAr/examples/rust/
- Legacy Python example: https://bitvortex.github.io/OSQAr/examples/python/

Note: GitHub Pages publishes one default example under `/example/` for backwards compatibility, and publishes all examples under `/examples/`.

GitHub Pages is built automatically on pushes to `main` via `.github/workflows/pages-deploy.yml`.

The docs default to the `furo` theme (with built-in light/dark mode). To force a fallback theme, set `OSQAR_SPHINX_THEME=alabaster`.

## Repository structure

- Framework documentation (general guides):
	- `index.rst` (framework landing page)
	- `docs/` (guides such as integrator/supplier usage)
	- `conf.py` (root Sphinx configuration; intentionally excludes `examples/**`)


- Reference implementations (example projects):
	- `examples/c_hello_world/` (C implementation + native JUnit-emitting tests)
	- `examples/cpp_hello_world/` (C++ implementation + native JUnit-emitting tests)
	- `examples/rust_hello_world/` (Rust implementation + native JUnit-emitting tests)
	- `examples/hello_world/` (legacy Python variant)


- Styling:
	- `_static/` (root static assets for framework docs)
	- `examples/*/_static/` (example-specific tweaks)

## Build locally

### Framework documentation (repo root)

```bash
poetry install
poetry run sphinx-build -b html . _build/html
open _build/html/index.html
```

### Reference example documentation

Build one of the language-specific examples:

```bash
poetry install
poetry run sphinx-build -b html examples/c_hello_world _build/html/example
open _build/html/example/index.html
```

Or build the C++ / Rust variants:

```bash
poetry run sphinx-build -b html examples/cpp_hello_world _build/html/example
poetry run sphinx-build -b html examples/rust_hello_world _build/html/example
```

Run an end-to-end example workflow (native tests → docs):

```bash
cd examples/c_hello_world
./build-and-test.sh
open _build/html/index.html
```

### Legacy Python example documentation (published under `/example/` today)

```bash
poetry install
poetry run sphinx-build -b html examples/hello_world _build/html/examples/python
open _build/html/examples/python/index.html
```

### Optional environment variables

- `OSQAR_SPHINX_THEME`: override theme (e.g., `furo`, `alabaster`)
- `PLANTUML_JAR`: point to a local `plantuml.jar` for offline PlantUML rendering

## Start here

If you are new to the repository:

1. Open the framework docs: https://bitvortex.github.io/OSQAr/
2. Then explore the example project: https://bitvortex.github.io/OSQAr/example/
3. If you want to copy a proven structure, start from `examples/c_hello_world/` (or `examples/cpp_hello_world/` / `examples/rust_hello_world/`) and replace its requirements/diagrams/tests with your system’s artifacts.

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
