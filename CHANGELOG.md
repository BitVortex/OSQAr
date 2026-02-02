# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-02-02

### Added
- Reproducible native build mode for the C/C++/Rust examples (`OSQAR_REPRODUCIBLE=1` + `SOURCE_DATE_EPOCH`)
- Optional Bazel integration for the C/C++/Rust examples, including a reproducible `--config=reproducible` mode
- CI pipeline that builds deterministic example “shipments” (docs + `needs.json` + traceability report + checksums + test report) and uploads them as a downloadable artifact (`osqar-example-shipments`)

### Changed
- Updated framework documentation and README to advertise reproducible builds and CI demo shipments
- Reframed OSQAr as a framework for producing, verifying, and integrating auditable evidence shipments
- Updated Copilot instructions to reflect Poetry-driven Sphinx builds and the shipment workflow
- CI now builds example shipments in separate jobs (matrix) and combines them afterwards for faster, isolated feedback

### Fixed
- Fixed a reStructuredText formatting issue in the framework docs that broke the Bazel example code block
- Fixed Bazel 9 compatibility for the C/C++ examples by explicitly loading `cc_*` rules from `rules_cc`
- Fixed CI doc builds after Bazel runs by excluding `bazel-*` output trees from Sphinx source discovery (prevents duplicate need IDs)
- Fixed Bazel wrapper scripts to write JUnit XML to a workspace path (prevents missing `test_results.xml` in CI)

## [0.2.4] - 2026-02-02

### Changed
- Simplified and restructured the framework documentation entry points to reduce hierarchy and redundancy
- Removed Markdown boilerplate docs under `docs/` in favor of the published Sphinx documentation
- Aligned README and framework docs feature descriptions with implemented tooling and configuration

### Added
- Prominent note that this repository is an example/boilerplate with LLM-assisted/generated content

## [0.2.3] - 2026-02-01

### Added
- Framework documentation on multi-user collaboration workflows (branching/merging strategies and conflict minimization)

### Fixed
- Cleaned up and expanded the shared TSIM lifecycle management chapter (removed duplicated content; added practical examples and actions)

## [0.2.2] - 2026-02-01

### Added
- Integrator multi-project workflow documentation ("Multi-project workflows")
- Workspace intake/verify tooling for multi-shipment workflows, including a "Subproject overview" (Markdown/JSON) with entrypoint links and needs.json-derived counts
- Optional supplier-provided shipment metadata file (osqar_project.json) with descriptive info, URLs, and origin

## [0.2.1] - 2026-02-01

### Added
- Shipment-oriented CLI commands to build docs, run tests, clean outputs, collect test reports, generate/verify checksums, and package shipments
- Role-focused workflows in the CLI for suppliers (`supplier prepare`) and integrators (`integrator verify`)
- Extensive lifecycle management documentation at framework level and included in each example

## [0.2.0] - 2026-02-01

### Added
- Complete Temperature Monitor (TSIM) example demonstrating OSQAr capabilities
- Interactive traceability with 111 clickable requirement links
- Automated test integration with JUnit XML import
- PlantUML architecture diagrams with requirement traceability
- Domain-agnostic thermal sensor interface module (TSIM)
- Comprehensive test suite with 13 test cases
- Sphinx documentation with sphinx-needs traceability
- Poetry-based dependency management
- GitHub Actions CI/CD template
- Linked requirement IDs across all documentation
- Export of machine-readable traceability (`needs.json`) for framework docs and examples
- Traceability validation tool producing `traceability_report.json`
- Shipment integrity tool to generate and verify `SHA256SUMS` for example build outputs
- Supplier/integrator documentation for shipment-style evidence transfer and verification
- Simple OSQAr CLI (`python -m tools.osqar_cli` and `./osqar`) for scaffolding and verification tasks

### Changed
- Version bumped to `0.2.0`
- CI and Pages workflows now run traceability checks and generate checksums for published examples
- Python compatibility constrained to `<3.14` due to upstream dependency support

### Fixed
- Root docs build no longer indexes `.venv` contents when building locally

### Changed
- Enhanced traceability matrix with clickable links
- Improved documentation structure with cross-references

### Fixed
- PlantUML rendering compatibility issues
- Python version compatibility (3.11+)

## [0.1.0] - 2026-01-23

### Added
- Initial release of OSQAr (Open Safety Qualification Architecture)
- Core Sphinx configuration with sphinx-needs
- Basic documentation boilerplate
- Poetry project setup
- Apache-2.0 License

### Changed
- N/A (initial release)

### Deprecated
- N/A (initial release)

### Removed
- N/A (initial release)

### Fixed
- N/A (initial release)

### Security
- N/A (initial release)