[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# OSQAr

Open Safety Qualification Architecture (OSQAr) — a Sphinx + sphinx-needs boilerplate for building **auditable, reuseable safety/compliance documentation** with:

- requirements + traceability (sphinx-needs)
- architecture diagrams (PlantUML)
- verification planning and traceability matrices
- extensive lifecycle management support

**Version:** 0.2.2 (see [CHANGELOG.md](CHANGELOG.md); versioning: https://semver.org/)

For license terms see the `LICENSE` file (Apache License 2.0).

## What you can do with OSQAr

OSQAr is documentation-first and aimed at producing **reviewable, exportable evidence** for safety- and compliance-related components (SEooC-style).

- Author structured requirements, architecture and verification plans (REQ/ARCH/TEST) in reStructuredText
- Generate traceability matrices and export the machine-readable trace graph (`needs.json`)
- Import and publish test results (e.g., JUnit XML) into the documentation
- Package an evidence “shipment” (rendered HTML + exports) and protect it with a `SHA256SUMS` integrity manifest
- Validate traceability rules (locally and in CI)
- As an integrator, intake multiple supplier shipments at once and get a consolidated **Subproject overview**
- Optionally attach supplier-provided metadata (`osqar_project.json`) including descriptive info, origin and URLs

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

## CLI

OSQAr ships a small, stdlib-only CLI to speed up common workflows (project scaffolding, evidence shipments, and integrator intake).

Run it either via Poetry:

```bash
poetry run python -m tools.osqar_cli --help
```

Or via the convenience wrapper (repo root):

```bash
./osqar --help
```

Typical commands:

```bash
# Scaffold a new project from a language template
poetry run python -m tools.osqar_cli new --language rust --name MySEooC --destination ./MySEooC

# Verify traceability from a built example output
poetry run python -m tools.osqar_cli traceability ./_build/html/needs.json --json-report ./_build/html/traceability_report.json

# Generate/verify shipment checksums
poetry run python -m tools.osqar_cli checksum generate --root ./_build/html --output ./_build/html/SHA256SUMS
poetry run python -m tools.osqar_cli checksum verify --root ./_build/html --manifest ./_build/html/SHA256SUMS

# Supplier: one-shot evidence shipment preparation (build docs, traceability, checksums, optional archive)
./osqar supplier prepare --project examples/rust_hello_world --clean --archive

# Supplier: optionally add metadata (description, URLs, origin) into the shipment root
./osqar shipment metadata write \
	--shipment examples/rust_hello_world/_build/html \
	--name "Rust Hello World" \
	--version "0.2.2" \
	--url repository=https://example.com/repo.git \
	--origin url=https://example.com/repo.git \
	--origin revision=<commit>

# Integrator: verify a received shipment (checksums, and optionally traceability)
./osqar integrator verify --shipment /path/to/received/shipment --traceability

# Integrator: intake multiple shipments and generate a Subproject overview
./osqar workspace intake \
	--root intake/received \
	--recursive \
	--output intake/archive/2026-02-01 \
	--traceability
```

See the framework docs for the evidence “shipment” workflow:

- https://bitvortex.github.io/OSQAr/ (Using the OSQAr Boilerplate)

## Start here

If you are new to the repository:

1. Open the framework docs: https://bitvortex.github.io/OSQAr/
2. Then explore the examples index: https://bitvortex.github.io/OSQAr/examples/
3. Pick an example language (guidance above): C/Rust preferred for safety-related embedded; Python is workstation-only.

## Notes

The file `docs/BOILERPLATE_USAGE.md` is a GitHub-readable overview. The authoritative framework documentation lives in `index.rst` and `docs/*.rst` and is what gets published to GitHub Pages.
