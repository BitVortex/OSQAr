# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - 2026-05-12

### Added
- **XLSX traceability matrix export** (`osqar traceability --format xlsx`): Excel export
  with bold headers and auto-fit columns. Requires `openpyxl` (optional). (#20)
- **Incremental shipment** (`osqar shipment prepare --incremental`): skip pipeline stages
  whose inputs haven't changed since last successful run. (#13)
- **Workspace combine** (`osqar workspace combine`): merge multiple project
  ``needs.json`` exports with namespace prefixes. (#17)
- **GPG manifest signing** (`osqar sign sign` / `sign verify`): detached signatures for
  shipment manifest authenticity (ISO 26262-8 §11.4.4). (#18)
- **GSN safety case support** (`osqar gsn generate`): generate gsn2x-compatible YAML from
  ``.. safety-case::`` needs, with optional PlantUML rendering. (#18)
- **Change impact analysis** (`osqar impact`): transitive closure on traceability links
  from a seed need ID. Tree/JSON output, configurable direction and depth. (#14)
- **Requirement baseline versioning** (`osqar baseline`): snapshot, list, and diff commands
  for versioned requirement baselines. (#15)
- **CSV traceability matrix export** (`osqar traceability --format csv`): spreadsheet-
  ready export with linked artifact columns. (#19)

### Changed
- **Documentation restructured**: new Getting Started guide, role-based guides (Supplier,
  Integrator), and Professional Deployment section (lifecycle management, multi-project
  workflows, collaboration). Complete CLI reference with all prefix flags.
- **CI integration guide**: uses OSQAr-cJSON as canonical reference with direct file links.
- **ASIL D claim language**: consistently framed as "ISO 26262 SEooC qualification attempt
  targeting ASIL D" across all public-facing documentation. Academic paper references
  removed from OSQAr-cJSON descriptions.

### Fixed
- `_load_needs` handles workspace-combined `needs.json` dict format (key regression after
  `osqar workspace combine`).
- `openpyxl` properly integrated as optional dependency in `pyproject.toml` evidence group;
  `poetry.lock` regenerated and in sync.
- Git hooks fixed for container environments: unset `VIRTUAL_ENV` so Poetry targets
  `$repo_root/.venv` instead of the agent's own venv; add `~/.local/bin`, `~/bin`,
  `~/.cargo/bin` to `PATH` in hooks.
- Rust toolchain (`cargo`, `rustc`) installed for `rust_hello_world` example validation.

## [0.7.3] - 2026-05-11

### Added
- **Change impact analysis** (`osqar impact`): transitive closure analysis on
  traceability links from a seed need ID. Tree/JSON output, configurable direction
  and depth. (#14)
- **Requirement baseline versioning** (`osqar baseline`): snapshot, list, and diff
  commands for versioned requirement baselines with structured change tracking. (#15)
- **CSV traceability matrix export** (`osqar traceability --format csv`):
  spreadsheet-ready export with linked artifact columns. (#19)
- **Incremental shipment preparation** (`osqar shipment prepare --incremental`):
  skip pipeline stages whose inputs haven't changed since last successful run,
  with `--force` to clear cache. (#13)
- **Workspace combine** (`osqar workspace combine`): merge multiple project
  ``needs.json`` exports with namespace prefixes for cross-project traceability.
  ``workspace traceability`` runs checks on the combined output. (#17)
- **GPG manifest signing** (`osqar sign sign` / ``sign verify``): detached
  signature support for shipment manifest authenticity (ISO 26262-8 §11.4.4). (#18)
- **GSN safety case support** (`osqar gsn generate`): generate gsn2x-compatible
  YAML from ``.. safety-case::`` needs, with optional rendering via gsn2x. (#18)

## [0.7.2] - 2026-05-11

*(v0.7.2 was re-tagged after adding CLI reference documentation; PyPI publish succeeded on the initial tag. v0.7.3 is the complete release including docs.)*

## [0.7.1] - 2026-05-08

### Added
- **CI Integration Guide** (`docs/ci_integration.rst`): public documentation covering the
  full verification-tooling-to-CI workflow — three-layer pipeline architecture
  (``build-and-test.sh`` → CI → OSQAr CLI), step-by-step integration, shipment
  assembly, local verification, and tag-based releases. Uses `OSQAr-cJSON`_ as the
  canonical reference implementation with direct links to all key files.
- **Dark-mode and PlantUML CSS fixes** (`furo-fixes.css`): sphinx-needs requirement
  tables now adapt to Furo's dark/light theme toggle via CSS variable overrides
  (no more white backgrounds in dark mode). PlantUML SVG diagrams are constrained to
  ``max-width: 100%`` with ``cursor: zoom-in`` affordance, preventing horizontal
  overflow from wide diagrams (e.g., 1933px component architecture SVG).
- ``furo-fixes.css`` is now included automatically in all scaffolded projects via
  ``osqar new`` and ``osqar workspace``, and in all template ``conf.py`` files.

### Changed
- **Example terminology audit** (26 fixes across ``python_hello_world``, ``tsim_docs``,
  ``c_shared_lib``): removed overclaiming and inappropriate safety terminology.
  "Compliance artifacts" → "Traceability outputs", "ISO 26262 Safety Goal" →
  "Example Safety Goal", "Safety Element (SEooC)" → "OSQAr-annotated component",
  "OSQAr-qualified" → "OSQAr-annotated". Examples now accurately describe
  themselves as OSQAr tooling demonstrations, not formal safety artifacts.

### Fixed
- sphinx-needs tables no longer render with white background in Furo dark mode.
- PlantUML diagrams no longer overflow the text column width.
- Example projects no longer contain misleading claims about ISO 26262 compliance
  or formal qualification status.

## [0.7.0] - 2026-05-08

### Added
- PlantUML-free build mode via ``OSQAR_NO_DIAGRAMS`` environment variable (#2, #11). When set to ``1`` or ``true``, ``sphinxcontrib.plantuml`` is excluded from the extension list and the entire PlantUML configuration block is skipped — enabling builds in offline/CI environments without Java or internet access. ``osqar new --no-diagrams`` permanently disables diagrams in scaffolded projects.
- Traceability CLI prefix overrides: ``--req-prefix``, ``--arch-prefix``, ``--test-prefix``, ``--code-prefix`` flags (all repeatable) available on ``osqar traceability``, ``osqar shipment prepare``, ``osqar shipment verify``, ``osqar shipment traceability``, and ``osqar doctor --traceability`` (#1, #12). Enables qualification projects (e.g., cJSON with ``VER_``/``IMPL_`` prefixes) to use custom need-ID conventions without modifying the framework.
- External source exemption for code traceability: ``--external-source`` flag (repeatable) on ``code_trace_check.py`` and ``osqar code-trace`` marks third-party/vendor directories as exempt from enforcement (#5, #8). External sources are still scanned for informational purposes, but IDs found only in external sources do not trigger enforcement violations — essential for qualifying read-only upstream libraries.
- Auto-generated gap documentation from ``osqar_project.json`` (#4, #9). The ``verification.gaps`` section supports structured entries (activity, status, reason, description, mitigation) and ``osqar shipment prepare`` auto-generates an RST list-table into ``_static/gaps.rst`` with human-readable labels. When no gaps are configured, a valid placeholder ensures the ``.. include`` directive in ``05_test_results.rst`` never breaks the Sphinx build.
- Configurable verification activity runner embedded in ``osqar shipment prepare`` (#3, #10). ``verification.run`` entries in ``osqar_project.json`` specify ``id``, ``label``, ``command`` (shell command), and ``report`` (glob pattern). Reports are collected into ``<shipment>/verification/``. ``--skip-verification`` flag bypasses all activities.
- PyPI template robustness improvements (#6, #7): ``osqar doctor`` now reports example template availability with source identification (git checkout or ``OSQAR_EXAMPLES_DIR``), ``--fallback-basic`` flag silently downgrades to the built-in basic template when examples are unavailable, and ``OSQAR_EXAMPLES_DIR`` env-var points to a local git checkout for pip-installed OSQAr.

### Changed
- All 14 ``conf.py`` files (root, examples, templates) now conditionally load PlantUML via the ``_NO_DIAGRAMS`` env-var guard, replacing the previous unconditional extension loading.
- ``osqar code-trace`` and ``code_trace_check.py`` now include external source metadata (``external_only`` counts, per-file/per-ID stats) in their reports.
- Template ``osqar_project.json`` includes commented examples for ``verification.run`` (sanitizer, cppcheck, gcov) and ``verification.gaps`` (valgrind, MISRA, MC/DC).

### Fixed
- Sphinx builds no longer fail when ``sphinxcontrib.plantuml`` is not installed and ``OSQAR_NO_DIAGRAMS`` is set — the extension is never imported.
- Code traceability enforcement no longer falsely reports violations for third-party source files that cannot be modified.

## [0.6.0] - 2026-02-12

### Added
- Workspace dependency awareness for OSQAr-qualified libraries:
	- Workspace reports/intakes now analyze supplier-declared dependencies from ``osqar_project.json``.
	- Dedup support: a single dependency shipment can satisfy multiple projects in the same workspace if the identity matches.
	- New enforcement flag: ``osqar workspace report|verify|intake --enforce-deps`` fails on missing/ambiguous/conflicting dependencies.
- ``osqar shipment pin`` helper command to compute a ``pin_sha256sums`` value for dependency declarations (SHA-256 of a shipment's ``SHA256SUMS``).

## [0.5.6] - 2026-02-07

### Changed
- Documentation rework: refreshed the framework entrypoint docs for clarity and consistency.
- Reworked the CLI reference to be the single authoritative command manual (synopsis/options/examples) and aligned terminology across the docs.
- Reworked the “Using the OSQAr Boilerplate” chapter to emphasize the mental model (project → shipment → workspace) and provide workflow recipes without duplicating the CLI reference.

### Fixed
- Framework documentation build no longer fails with ``sphinx-build -W`` due to a reStructuredText title underline length error.

## [0.5.5] - 2026-02-07

### Fixed
- ``osqar workspace verify`` now correctly treats combined example workspace bundles (release assets) as containers and verifies the shipments under ``shipments/`` instead of attempting to verify the workspace root as a single shipment.
- Shipment verification code-trace now locates ``needs.json`` via recursive discovery (aligns with existing traceability behavior).

### Added
- ``osqar setup`` command to verify (optional checksum), extract, and then verify a downloaded shipment/workspace ZIP.

## [0.5.4] - 2026-02-06

### Fixed
- Framework documentation build now succeeds with ``sphinx-build -W`` by excluding packaged scaffold resources (``osqar_data/**``) from the framework docs build.
- Scaffold template trace links are now internally consistent (no unknown outgoing need links).
- Added missing ``roman`` dependency required by Sphinx in some environments.

## [0.5.3] - 2026-02-06

### Changed
- Documentation now prefers the PyPI/pipx-installed CLI invocation (``osqar ...``) over repo-root wrappers.

### Fixed
- Regenerated ``poetry.lock`` to match ``pyproject.toml`` (fixes CI lockfile consistency checks).

## [0.5.2] - 2026-02-06

### Added
- PyPI-distributable OSQAr CLI (`pipx install osqar`) with packaged scaffolding templates.

### Changed
- `osqar new` now loads templates from packaged resources (works when installed from PyPI; examples are not shipped).

## [0.5.1] - 2026-02-06

### Changed
- Refactored the OSQAr CLI internals into per-command modules under `tools/` (thin `tools/osqar_cli.py` entrypoint).
- Removed the previously monolithic `tools/osqar_cli_app/` implementation to improve maintainability.

### Fixed
- Workspace intake overview now shows project names (instead of a blank Project column).

## [0.5.0] - 2026-02-06

### Added
- Extensible JSON configuration for projects and workspaces:
	- `osqar_project.json` supports `commands.docs`, `commands.test`, `commands.build`
	- `osqar_workspace.json` supports `defaults.exclude` and integrator-side hooks
- Pre/post hook execution around key CLI events (shipment and workspace workflows)
- Hook kill switch: `--no-hooks` and environment `OSQAR_DISABLE_HOOKS=1`
- Integrator-side extra verification commands:
	- `shipment verify --verify-command '<cmd>'` (repeatable)
	- `workspace verify --verify-command '<cmd>'` (repeatable)
- Dedicated documentation page: “Configuration and hooks”

### Changed
- `build-docs` (top-level shorthand) now also accepts `--config` and `--no-hooks` for parity with `shipment build-docs`
- Documentation now clarifies the security model: do not execute untrusted commands/hooks from received bundles

## [0.4.2] - 2026-02-06

### Added
- Workspace HTML overview now follows the main docs theme and includes shared CSS fixes

### Changed
- Workspace HTML overview renders explicit verification status values for checksums/traceability (OK / FAIL / skipped)

### Fixed
- Workspace HTML overview no longer appears visually empty in some themes
- Workspace overview renders placeholders for missing shipment metadata fields (version/origin)

## [0.4.1] - 2026-02-06

### Added
- `osqar open-docs` convenience command for opening built HTML docs
- `osqar build-docs --open` to build and open docs in one step
- Generalized shipment workflows (`shipment prepare`, `shipment verify`) with supplier/integrator commands kept as aliases
- `osqar doctor` tooling diagnostics (Poetry/Sphinx/PlantUML checks)

### Changed
- Documentation now consistently prefers `./osqar` shorthand for traceability and checksums

## [0.4.0] - 2026-02-05

### Added
- Central CLI reference documentation and reduced CLI duplication across guides
- Cross-platform `osqar` wrapper scripts (`osqar`, `osqar.cmd`, `osqar.ps1`) and a shorthand `build-docs` command
- Minimal “basic” project templates (C/C++/Rust/Python) with shared template overlays
- Poetry-managed scaffolds (shared `pyproject.toml` + `poetry.lock`) for fixed documentation/tooling dependencies

### Changed
- Documentation now prefers `./osqar build-docs` over raw `sphinx-build` invocations
- `osqar build-docs` prefers running Sphinx inside the target project’s Poetry environment when available
- Documentation navigation: moved CLI reference and project setup under the Framework section

### Fixed
- Migrated project metadata to PEP 621 (`[project]`) to avoid Poetry deprecation warnings

## [0.3.1] - 2026-02-03

### Added
- Embedded JUnit test tables in example documentation (`test-results`), with CI/Pages generating per-example `test_results.xml` before Sphinx builds
- Embedded per-example code coverage evidence (`coverage_report.txt`) in CI/Pages builds
- Embedded per-example complexity evidence (`complexity_report.txt`) adjacent to coverage in the shared test results chapter

### Fixed
- Normalized C/C++/Rust JUnit XML writers to include `errors`, `skipped`, and `time` attributes (prevents `-1` values in rendered summaries)

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
- Workspace intake/verify tooling for multi-shipment workflows, including a "Subproject overview" (HTML/JSON) with entrypoint links and needs.json-derived counts
- Optional supplier-provided shipment metadata file (osqar_project.json) with descriptive info, URLs, and origin

## [0.2.1] - 2026-02-01

### Added
- Shipment-oriented CLI commands to build docs, run tests, clean outputs, collect test reports, generate/verify checksums, and package shipments
- Unified shipment/workspace workflows for producing and verifying evidence bundles
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
- Simple OSQAr CLI (`./osqar` and Windows wrappers `osqar.cmd` / `osqar.ps1`) for scaffolding and verification tasks

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