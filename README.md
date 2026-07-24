[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/bitvortex/OSQAr/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/bitvortex/OSQAr/actions/workflows/ci.yml)
[![Docs](https://github.com/bitvortex/OSQAr/actions/workflows/pages-deploy.yml/badge.svg?branch=main)](https://github.com/bitvortex/OSQAr/actions/workflows/pages-deploy.yml)

# OSQAr — Open Safety Qualification Architecture

OSQAr is an open framework for creating, checking, and exchanging auditable
evidence packages for safety-related engineering. It combines structured
requirements and architecture documentation, explicit traceability, verification
results, integrity manifests, and reproducible shipment workflows.

OSQAr performs mechanical checks and records their results. It does **not**
determine whether a system is safe, compliant, certified, or qualified.

## Quick start

Install the CLI with [`pipx`](https://pipx.pypa.io/):

```bash
pipx install osqar
osqar new --language c --name hello_safety
cd hello_safety
osqar build-docs
osqar open-docs
```

The default scaffold is intentionally generic. Adapt its needs, evidence model,
acceptance criteria, and standards references to the project and its assurance
plan.

## Core workflow

1. **Scaffold a project.** Start from a basic C, C++, Rust, or Python project.
2. **Describe the engineering evidence.** Author requirements, architecture,
   verification activities, results, assumptions, and lifecycle records in
   reStructuredText with `sphinx-needs` links.
3. **Check the evidence graph.** Build the documentation, validate traceability,
   inspect change impact, and record machine-readable reports.
4. **Prepare a shipment.** Assemble the declared evidence, generate checksums,
   and optionally create a distributable archive.
5. **Verify and integrate.** Verify received shipments before intake, preserve
   their provenance, and combine accepted projects in an integrator workspace.

A typical producer-side command is:

```bash
osqar shipment prepare --archive
```

Use `osqar --help` and `osqar <command> --help` for the complete command surface.

## Capabilities

### Evidence and traceability

- Structured requirements, architecture, verification, result, and lifecycle
  records using Sphinx and `sphinx-needs`.
- Machine-readable `needs.json` exports and CSV/XLSX traceability matrices.
- Change-impact traversal and versioned requirement baselines.
- Typed traceability profiles with explicit direction, type, cardinality,
  lifecycle, cycle, orphan, and result-state rules.
- Code-reference scanning for need identifiers in implementation and tests.
- GSN-shaped safety-case views rendered through PlantUML or gsn2x.

### Verification and provenance

- Fail-closed framework evidence validation with machine-readable reports.
- Standards-neutral claim catalogs with stable reference identifiers and typed
  claim links.
- Project-supplied evidence anchors rather than trust in local status labels.
- SHA-256 shipment manifests and optional detached GPG signatures.
- Versioned closed release manifests with file size, digest, identity, path, and
  exact-set checks.
- Explicit tool-reliance boundaries for project-specific assurance decisions.

### Delivery and integration

- Basic scaffolds for C, C++, Rust, and Python.
- Documentation builds with optional PlantUML-free operation for offline CI.
- One-command shipment preparation and archive generation.
- Workspace verification, intake, dependency-closure checks, reporting, and
  cross-project traceability.
- Framework bundles, example workspaces, and release artifacts published through
  [GitHub Releases](https://github.com/BitVortex/OSQAr/releases).

## Interpreting OSQAr results

OSQAr distinguishes mechanical validation from engineering judgment:

- A successful command means that the executed, versioned rules passed for the
  supplied inputs.
- It does not establish that requirements are complete or technically correct.
- It does not validate a standards interpretation or replace confirmation
  measures, independent review, safety assessment, or tool qualification.
- Safety integrity levels, acceptance criteria, evidence authorities, and tool
  reliance must be defined and justified for the specific project.
- Illustrative catalogs, examples, and generated documents are starting points,
  not compliance or certification evidence by themselves.

## Scaffolding

The recommended starting point is the default `basic` scaffold:

```bash
osqar new --language cpp --name controller
osqar new --language rust --name monitor --no-diagrams
```

Reference-project scaffolding may be available from a source checkout. Run
`osqar new --help` to inspect the options provided by the installed version.
Generated projects currently target Python `>=3.9,<3.14`; the framework package
targets Python `>=3.9,<3.15`.

## Documentation and downloads

- [Framework documentation](https://bitvortex.github.io/OSQAr/)
- [Reference examples](https://bitvortex.github.io/OSQAr/examples)
- [Published releases and evidence bundles](https://github.com/BitVortex/OSQAr/releases)
- [Issue tracker](https://github.com/BitVortex/OSQAr/issues)

## Development

```bash
git clone https://github.com/BitVortex/OSQAr.git
cd OSQAr
poetry install
./osqar build-docs
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for contributor setup, tests, and review
expectations.

## License

OSQAr is distributed under the [Apache License 2.0](LICENSE).
