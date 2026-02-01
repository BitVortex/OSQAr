# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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