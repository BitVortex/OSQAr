[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI (Tests and Example Shipments)](https://github.com/bitvortex/OSQAr/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/bitvortex/OSQAr/actions/workflows/ci.yml)
[![Docs (GitHub Pages)](https://github.com/bitvortex/OSQAr/actions/workflows/pages-deploy.yml/badge.svg?branch=main)](https://github.com/bitvortex/OSQAr/actions/workflows/pages-deploy.yml)

# OSQAr

Open Safety Qualification Architecture (OSQAr) is a documentation-first framework for producing and integrating **auditable evidence shipments** for safety/compliance work.

A shipment is a reviewable bundle that contains **Sphinx documentation with maintained traceability**, plus the **implementation**, **tests**, and **analysis/verification reports** needed to audit the evidence end-to-end.

## Features / use cases

- Write structured requirements, architecture and verification plans in reStructuredText (traceability via `sphinx-needs`)
- Render architecture diagrams with PlantUML (embedded in the docs)
- Export machine-readable traceability (`needs.json`) alongside HTML
- Generate traceability views (e.g., matrices) and keep verification coverage reviewable
- Verify traceability rules and produce audit-friendly reports
- Package documentation + evidence artifacts and protect them with checksum manifests
- Integrate multiple supplier shipments as an integrator (multi-project intake workflows)
- Scaffold new projects from minimal templates (C/C++/Rust/Python) via the OSQAr CLI
- Use lifecycle management and collaboration workflows for multi-user teams
- Run reproducible native builds for the C/C++/Rust reference examples (optional Bazel integration)
- Use CI-produced demo shipments and downloadable release bundles as a starting point for your own project setup

## Docs and examples

- Framework docs (published): https://bitvortex.github.io/OSQAr/
- Examples index (published): https://bitvortex.github.io/OSQAr/examples/
- Download pre-built bundles (framework docs + tooling, example shipments): https://github.com/bitvortex/OSQAr/releases

## Quickstart

Dependencies:

- Python `>=3.9` (see `pyproject.toml`)
- Poetry: https://python-poetry.org/
- Optional for offline PlantUML rendering: Java and/or PlantUML (`PLANTUML_JAR` also works). If neither is available, the build falls back to the public PlantUML web service (requires internet).

Build the framework documentation (repo root):

```bash
poetry install
./osqar build-docs
```

Build an example’s documentation (choose one):

```bash
./osqar build-docs --project examples/c_hello_world
./osqar build-docs --project examples/cpp_hello_world
./osqar build-docs --project examples/rust_hello_world
./osqar build-docs --project examples/python_hello_world
```

Run an example end-to-end (tests → docs), including optional evidence tooling:

```bash
poetry install --with evidence
cd examples/c_hello_world
./build-and-test.sh
```

Create a new project (minimal template scaffold):

```bash
# Default template profile is "basic" (lean scaffold)
./osqar new --language c --name MySEooC --destination ../MySEooC
```

Notes:

- The `./osqar` wrapper is intended to be run from the OSQAr repo root.
- On Windows, use `osqar.cmd` or `osqar.ps1` from the repo root.
- Fallback (no wrapper): `poetry run python -m tools.osqar_cli ...`
