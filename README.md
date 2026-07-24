[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/bitvortex/OSQAr/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/bitvortex/OSQAr/actions/workflows/ci.yml)
[![Docs](https://github.com/bitvortex/OSQAr/actions/workflows/pages-deploy.yml/badge.svg?branch=main)](https://github.com/bitvortex/OSQAr/actions/workflows/pages-deploy.yml)

# OSQAr — Open Safety Qualification Architecture

OSQAr helps engineering teams **author, check, package, and exchange auditable
evidence** for safety-related work. A project can connect requirements,
architecture, implementation, verification activities, results, assumptions,
and lifecycle records, then publish them as an integrity-protected shipment.

OSQAr automates repeatable, versioned checks. It does **not** decide whether a
system is safe or whether evidence is technically sufficient. A passing result
does not establish compliance, certification, tool qualification, or ASIL
qualification.

## Start here

Install the CLI with [`pipx`](https://pipx.pypa.io/), create a generic project,
and render its documentation:

```bash
pipx install osqar
osqar new --language rust --name first_osqar_project
cd first_osqar_project
osqar build-docs
osqar open-docs
```

The generated project is a starting structure. Replace its example needs,
acceptance criteria, and evidence placeholders with project-authorized content.

Next steps:

1. Read the [five-minute guide](docs/getting_started.rst).
2. Learn the [project → shipment → workspace workflow](docs/using_the_boilerplate.rst).
3. Use the [CLI reference](docs/cli_reference.rst) when you need every option,
   exit code, and resolution rule.

The rendered documentation is available at the
[OSQAr documentation site](https://bitvortex.github.io/OSQAr/).

## Choose the right starting point

### Basic scaffold — recommended for a new project

Use `basic` when you want a small, standards-neutral project structure:

```bash
osqar new --language c --name controller
osqar new --language rust --name monitor --no-diagrams
```

Basic scaffolds are available for C, C++, Python, and Rust.

### ASIL-target examples — learn from explicit, incomplete links

Use these examples to explore how a project **targeting ASIL D** might link
bounded standards claims to draft requirements, implementation, planned
verification, and pending evidence:

```bash
osqar new --language c --template asil_example_c --name asil_c_walkthrough
osqar new --language rust --template asil_example_rust --name asil_rust_walkthrough
```

Both examples deliberately keep evidence pending and label project policy as
project policy. They demonstrate exemplary links; generating or building one
does not establish ASIL qualification. Before project use, replace the example
catalog declarations, interpretations, requirements, acceptance criteria, tool
assumptions, and evidence records.

See [Understanding the ASIL-target examples](docs/asil_examples.rst) for the
common evidence model, language-specific differences, and tailoring checklist.

## The OSQAr workflow

1. **Author** — describe stable needs and explicit links in reStructuredText.
2. **Build** — render readable Sphinx documentation and export `needs.json`.
3. **Check** — run traceability, evidence-state, impact, checksum, and policy
   checks selected by the project.
4. **Package** — prepare an evidence shipment and its integrity manifest.
5. **Verify and integrate** — validate received bytes before intake and preserve
   provenance in a workspace.

A common producer command is:

```bash
osqar shipment prepare --project . --archive
```

A common integrator sequence is:

```bash
osqar shipment verify --shipment received/component
osqar workspace intake --root workspace --shipment received/component
osqar workspace verify --root workspace --recursive
```

Run `osqar --help` or `osqar <command> --help` for installed-version help.

## Documentation map

### New users

- [Getting started](docs/getting_started.rst) — install, scaffold, build, inspect,
  and prepare a first shipment.
- [Understanding the ASIL-target examples](docs/asil_examples.rst) — compare the
  C and Rust examples without confusing a target with achieved qualification.
- [Project setup](docs/project_setup_from_scratch.rst) — start cleanly or migrate
  an existing codebase.

### Task guides

- [Supplier guide](docs/suppliers_guide.rst) — produce an evidence shipment.
- [Integrator guide](docs/integrators_guide.rst) — verify and intake a shipment.
- [CI integration](docs/ci_integration.rst) — run repeatable checks in automation.
- [Lifecycle management](docs/lifecycle_management.rst) — baselines, changes,
  and release discipline.
- [Multi-project workflows](docs/multi_project_workflows.rst) — dependency closure
  and workspace operations.

### Power-user reference

- [CLI reference](docs/cli_reference.rst) — commands, flags, outputs, and exits.
- [Configuration and hooks](docs/configuration_and_hooks.rst) — project and
  workspace configuration.
- [Evidence acceptance](docs/evidence_acceptance.rst) — controlled evidence
  states and fail-closed validation boundaries.
- [Typed traceability](docs/typed_traceability.rst) — directed profiles,
  qualification rules, and API projection.
- [Tool-reliance boundary](docs/tool_reliance_boundary.rst) — separate mechanical
  checks from project-specific tool assurance.
- [Release manifest](docs/release_manifest.rst) — closed payload verification.

## What OSQAr checks—and what it cannot conclude

A successful command means only that the named rules executed successfully for
the supplied inputs. Depending on the command, OSQAr can check structure,
identifiers, authored link direction, profile rules, evidence state, file
identity, checksums, manifests, and closed payload membership.

OSQAr cannot establish that:

- requirements or architecture are complete or technically correct;
- a standards interpretation is valid or applicable;
- verification methods and acceptance criteria are adequate;
- evidence is independent, sufficient, or accepted by an authority;
- a tool is qualified for a specific relied-upon use; or
- a system or component is safe, compliant, certified, or qualified.

Those conclusions require competent project-specific engineering, review,
assessment, and authorization.

## Development

```bash
git clone https://github.com/BitVortex/OSQAr.git
cd OSQAr
poetry install
./osqar build-docs
poetry run python -m pytest -q tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contributor setup and review gates.
Published archives are available from
[GitHub Releases](https://github.com/BitVortex/OSQAr/releases).

## License

OSQAr is distributed under the [Apache License 2.0](LICENSE).
