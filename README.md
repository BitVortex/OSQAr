[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# OSQAr

Open Safety Qualification Architecture (OSQAr) — a Sphinx + sphinx-needs boilerplate for building **auditable safety/compliance documentation** with:

- requirements + traceability (sphinx-needs)
- architecture diagrams (PlantUML)
- verification planning and traceability matrices

**Version:** 0.2.0 (see [CHANGELOG.md](CHANGELOG.md); versioning: https://semver.org/)

For license terms see the `LICENSE` file (Apache License 2.0).

## Documentation (GitHub Pages)

- Framework documentation (landing page): https://bitvortex.github.io/OSQAr/
- Examples index: https://bitvortex.github.io/OSQAr/examples/

Published examples (built docs):

- C example: https://bitvortex.github.io/OSQAr/examples/c/
- Rust example: https://bitvortex.github.io/OSQAr/examples/rust/
- C++ example: https://bitvortex.github.io/OSQAr/examples/cpp/
- Python demo example (workstation): https://bitvortex.github.io/OSQAr/examples/python/

GitHub Pages is built automatically on pushes to `main` via `.github/workflows/pages-deploy.yml`.

The docs default to the `furo` theme (with built-in light/dark mode). To force a fallback theme, set `OSQAR_SPHINX_THEME=alabaster`.

## Language guidance (examples)

- For safety-related embedded projects, prefer **C** or **Rust** as a starting point.
- **C++** is common in industry, but is usually harder to constrain and qualify for safety.
- The **Python** example is a workstation demo to make the workflow easy to run; it is not intended for embedded targets.

## Repository structure

- Framework documentation (general guides):
	- `index.rst` (Sphinx source for the framework landing page)
	- `docs/` (Sphinx sources for guides such as integrator/supplier usage)
	- `conf.py` (root Sphinx configuration; intentionally excludes `examples/**`)


- Reference implementations (example projects):
	- `examples/c_hello_world/` (source for the C example → published at https://bitvortex.github.io/OSQAr/examples/c/)
	- `examples/rust_hello_world/` (source for the Rust example → published at https://bitvortex.github.io/OSQAr/examples/rust/)
	- `examples/cpp_hello_world/` (source for the C++ example → published at https://bitvortex.github.io/OSQAr/examples/cpp/)
	- `examples/python_hello_world/` (source for the Python workstation demo → published at https://bitvortex.github.io/OSQAr/examples/python/)
	- `examples/tsim_docs/` (shared TSIM chapter sources included by all example projects)


- Styling:
	- `_static/` (root static assets for framework docs)
	- `examples/*/_static/` (example-specific tweaks)

## Build locally

If you just want to read the docs, prefer the published site:

- Framework docs: https://bitvortex.github.io/OSQAr/
- Examples index: https://bitvortex.github.io/OSQAr/examples/

### Framework documentation (repo root)

```bash
poetry install
poetry run sphinx-build -b html . _build/html
```

### Reference example documentation

Build one of the language-specific examples (pick the language that matches your product):

```bash
poetry install
poetry run sphinx-build -b html examples/c_hello_world _build/html/examples/c
```

Or build the C++ / Rust variants:

```bash
poetry run sphinx-build -b html examples/cpp_hello_world _build/html/examples/cpp
poetry run sphinx-build -b html examples/rust_hello_world _build/html/examples/rust
```

Run an end-to-end example workflow (native tests → docs):

```bash
cd examples/c_hello_world
./build-and-test.sh
```

### Python demo example (published under `/examples/python/`)

```bash
poetry install
poetry run sphinx-build -b html examples/python_hello_world _build/html/examples/python
```

### Optional environment variables

- `OSQAR_SPHINX_THEME`: override theme (e.g., `furo`, `alabaster`)
- `PLANTUML_JAR`: point to a local `plantuml.jar` for offline PlantUML rendering

## Start here

If you are new to the repository:

1. Open the framework docs: https://bitvortex.github.io/OSQAr/
2. Then explore the examples index: https://bitvortex.github.io/OSQAr/examples/
3. Pick an example language (guidance above): C/Rust preferred for safety-related embedded; Python is workstation-only.

## Notes

The file `docs/BOILERPLATE_USAGE.md` is a GitHub-readable overview. The authoritative framework documentation lives in `index.rst` and `docs/*.rst` and is what gets published to GitHub Pages.
