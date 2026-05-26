[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/bitvortex/OSQAr/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/bitvortex/OSQAr/actions/workflows/ci.yml)
[![Docs](https://github.com/bitvortex/OSQAr/actions/workflows/pages-deploy.yml/badge.svg?branch=main)](https://github.com/bitvortex/OSQAr/actions/workflows/pages-deploy.yml)

# OSQAr — Open Safety Qualification Architecture

**Auditable evidence shipments with traceability.** Write requirements, architecture, and verification plans in reStructuredText. Link them with `sphinx-needs`. Package into integrity-protected shipments. Integrate across teams.

```bash
pipx install osqar
osqar new --language c --name hello_safety && cd hello_safety
osqar build-docs && osqar open-docs
```

## Who this is for

| Role | Does |
|---|---|
| **Supplier** | Produce auditable evidence shipments (docs + code + tests + checksums) |
| **Integrator** | Verify, intake, and archive received shipments; enforce dependency closure |
| **Internal team** | Standardize evidence packaging across subprojects and CI |

## Quick links

- 📖 **Docs**: [bitvortex.github.io/OSQAr](https://bitvortex.github.io/OSQAr/) — full framework documentation
- 📦 **Examples**: [bitvortex.github.io/OSQAr/examples](https://bitvortex.github.io/OSQAr/examples/) — C, C++, Rust, Python reference projects
- 🔬 **Full demo**: [OSQAr‑cJSON](https://github.com/BitVortex/OSQAr-cJSON) — ISO 26262 SEooC qualification attempt targeting ASIL D (88% coverage, 162 tests)
- 📥 **Downloads**: [GitHub Releases](https://github.com/bitvortex/OSQAr/releases) — pre-built framework bundles and example workspaces

## Features

**Documentation & traceability**

- Structured requirements, architecture, verification plans via `sphinx-needs` + reStructuredText
- PlantUML architecture diagrams embedded in docs
- Machine-readable `needs.json` exports with full traceability graph
- CSV and Excel (`--format xlsx`) traceability matrix exports for auditor review
- Change impact analysis (`osqar impact`) from any seed requirement
- Versioned requirement baselines with snapshot/list/diff (`osqar baseline`)
- Requirement ID prefix overrides (`--req-prefix`, `--arch-prefix`, etc.)

**Shipment & integrity**

- One-shot shipment preparation (`osqar shipment prepare --archive`)
- SHA256SUMS manifest generation and verification
- GPG detached signature support (`osqar sign create` / `osqar sign verify`)
- Incremental mode — only rebuild changed stages
- Project metadata declaration with OSQAr-qualified dependency pins

**Verification & CI**

- Traceability rule enforcement (REQ→ARCH, ARCH→REQ, REQ→TEST)
- Code trace scanning with enforcement (`osqar code-trace`)
- Configurable verification activities (sanitizers, static analysis, fuzzing)
- Auto-generated gap documentation from `osqar_project.json`
- PlantUML-free build mode (`OSQAR_NO_DIAGRAMS=1`) for offline/CI
- Scaffold projects with `osqar new --no-diagrams` to permanently disable diagrams

**Multi-project & organization**

- Workspace orchestration: list, report, verify, intake, combine
- Cross-project traceability via namespace-prefixed workspace combine
- Dependency closure enforcement across received shipments
- Lifecycle management and collaboration workflows for multi-user teams
- Reproducible native builds (C/C++/Rust, optional Bazel integration)
- Extensible via project/workspace JSON config + command hooks

**Getting started as a developer**

```bash
git clone https://github.com/BitVortex/OSQAr.git
cd OSQAr
poetry install
osqar build-docs && osqar open-docs
```

For the full contributor setup (editable install, evidence tools, CI), see the [framework docs](https://bitvortex.github.io/OSQAr/).
