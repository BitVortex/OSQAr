[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI (Tests and Builds)](https://github.com/bitvortex/OSQAr/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/bitvortex/OSQAr/actions/workflows/ci.yml)
[![Docs (GitHub Pages)](https://github.com/bitvortex/OSQAr/actions/workflows/pages-deploy.yml/badge.svg?branch=main)](https://github.com/bitvortex/OSQAr/actions/workflows/pages-deploy.yml)

# OSQAr

Open Safety Qualification Architecture (OSQAr) is a documentation-first framework for producing and integrating **auditable evidence shipments** for safety/compliance work.

A shipment is a reviewable bundle that contains **Sphinx documentation with maintained traceability**, plus the **implementation**, **tests**, and **analysis/verification reports** needed to audit the evidence end-to-end.

## Who this is for

OSQAr is for teams that need **auditable, reviewable engineering evidence** with traceability (requirements ↔ architecture ↔ verification), especially when evidence must be transferred between organizations.

Typical roles and workflows:

- **Suppliers**: build docs and verification evidence, then prepare integrity-protected shipments (HTML + `needs.json` + reports + `SHA256SUMS`).
- **Integrators**: verify received shipments (checksums, optional traceability re-check), run extra integrator-side checks, and archive multiple shipments into a single intake with a consolidated HTML overview.
- **Internal teams**: use the same shipment workflow to standardize evidence packaging across subprojects and CI.

## Features / use cases

- Write structured requirements, architecture and verification plans in reStructuredText (traceability via `sphinx-needs`)
- Render architecture diagrams with PlantUML (embedded in the docs)
- Export machine-readable traceability (`needs.json`) alongside HTML
- Generate traceability views (e.g., matrices) and keep verification coverage reviewable
- Verify traceability rules and produce audit-friendly reports
- Trace requirements, architecture and tests into the actual code and check for consistency
- Package documentation + evidence artifacts and protect them with checksum manifests
- Integrate multiple shipments in a workspace and review a consolidated overview
- Declare and enforce workspace dependency closure for OSQAr-qualified libraries (id/version/pin), including logical deduplication when a single dependency shipment satisfies multiple dependents
- Extend workflows via project and workspace configuration (custom commands + hooks)
- Use lifecycle management and collaboration workflows for multi-user teams
- Run reproducible native builds for the C/C++/Rust reference examples with optional Bazel integration
- Use CI-produced demo shipments and downloadable release bundles as a starting point for your own project setup, or scaffold new projects from minimal templates (C/C++/Rust/Python) via the OSQAr CLI

## Docs and examples

- Framework docs (published): https://bitvortex.github.io/OSQAr/
- Examples index (published): https://bitvortex.github.io/OSQAr/examples/
- Download pre-built bundles (framework bundle, example workspace): https://github.com/bitvortex/OSQAr/releases

## Quickstart

Dependencies:

- Python `>=3.9` (see `pyproject.toml`)
- Poetry: https://python-poetry.org/
- Optional for offline PlantUML rendering: Java and/or PlantUML (`PLANTUML_JAR` also works). If neither is available, the build falls back to the public PlantUML web service (requires internet).

Install the OSQAr CLI (recommended for users):

```bash
pipx install osqar
osqar --help
```

Quickstart from a downloaded Release bundle (example workspace):

```bash
# Download the example workspace ZIP (and its .sha256) from GitHub Releases.
# Then verify checksum (if present), extract it, and verify all contained shipments:
osqar setup osqar_example_workspace_<tag>.zip
```

Notes:

- The PyPI package includes the **minimal project templates** used by `osqar new`.
- The full reference `examples/` are not shipped on PyPI; use the git repo or release bundles if you need them.

Build the framework documentation (repo root):

```bash
poetry install
osqar build-docs
osqar open-docs
```

Build an example’s documentation (choose one):

```bash
osqar build-docs --project examples/c_hello_world
osqar build-docs --project examples/cpp_hello_world
osqar build-docs --project examples/rust_hello_world
osqar build-docs --project examples/python_hello_world
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
osqar new --language c --name MySEooC --destination ../MySEooC
```

Notes:

- If you are working from a git clone and did not install the CLI via pipx, you can run the repo-root wrappers instead: `./osqar` (Linux/macOS) or `osqar.cmd` / `osqar.ps1` (Windows).

## Extensibility (custom commands + hooks)

OSQAr supports optional JSON configuration files so teams can plug in their own build/test/verification tooling while keeping OSQAr’s evidence structure, traceability, and integrity checks.

Project-side config: `osqar_project.json`

- Put this file in a project root (supplier/dev side).
- Use `commands.test` and `commands.docs` to override how tests and docs are executed.
- Use `hooks.pre` / `hooks.post` to run pre/post actions around OSQAr command events.
- If your project (library) depends on other OSQAr-qualified libraries, declare them under `dependencies` so integrator workspaces can validate dependency closure.

Example:

```json
{

  "id": "LIB_CONSUMER",
  "version": "1.2.3",
  "dependencies": [
    {
      "id": "LIB_PROVIDER",
      "version": "2.0.0",
      "pin_sha256sums": "<sha256-of-SHA256SUMS-file-bytes>"
    }
  ],

  "commands": {
    "test": "OSQAR_REPRODUCIBLE=1 ./build-and-test.sh",
    "docs": "poetry run sphinx-build -b html . _build/html"
  },
  "hooks": {
    "pre": {
      "shipment.prepare": "echo pre-prepare"
    },
    "post": {
      "shipment.prepare": ["echo post-prepare", "echo done"]
    }
  }
}
```

Compute a dependency pin from a built/received shipment directory:

```bash
osqar shipment pin --shipment /path/to/LIB_PROVIDER_shipment
```

Integrator workspaces can enforce dependency closure across all received shipments:

```bash
osqar workspace verify --root intake/received --recursive --enforce-deps
```

Integrator-side config: `osqar_workspace.json`

- Put this file in a trusted integrator workspace root and use it with `workspace report/verify/intake`.
- You can also attach extra integrator-side checks to shipment verification via `--verify-command` (repeatable).
- For `shipment verify`, use `--config-root <trusted_dir>` to load workspace config from a trusted location.

Hook kill switch:

- Set `OSQAR_DISABLE_HOOKS=1` or pass `--no-hooks`.

See the published docs for the full reference (supported keys, hook events, and security notes).
