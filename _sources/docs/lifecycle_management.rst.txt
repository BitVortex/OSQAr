====================
Lifecycle Management
====================

Purpose
=======

This chapter defines an audit-friendly **lifecycle management** approach for OSQAr-based projects.
It covers how to control change, keep evidence reproducible, and manage supplier/integrator handoffs
across releases.

OSQAr is **documentation-first**: the primary lifecycle artifact is a controlled documentation set that
links requirements ↔ architecture ↔ verification and can be shipped as an evidence bundle.

For team-scale practices (branching, merging, conflict minimization), see :doc:`collaboration_workflows`.

Scope
=====

This guide applies to:

- the OSQAr framework (this repository and its configuration patterns)
- OSQAr-based supplier projects (SEooC documentation + implementation + verification)
- integrators consuming supplier shipments (intake, validation, archiving)

Definitions
===========

**Shipment (evidence bundle)**
  A directory that an organization transfers and archives as evidence.
  In OSQAr, a shipment is an evidence bundle that contains **Sphinx documentation with maintained traceability**, plus the **implementation**, **tests**, and **analysis/verification reports** required to review evidence end-to-end, protected by integrity metadata.

**Supplier**
  The party producing the SEooC and its evidence package.

**Integrator**
  The party integrating the SEooC into a context-specific system and completing the safety case.

Lifecycle objectives
====================

A lifecycle process for safety-related documentation should achieve, at minimum:

- **Reproducibility**: rebuild the same documentation and checks from the same inputs
- **Traceability continuity**: stable IDs and links across releases (diffable and reviewable)
- **Integrity**: tamper detection for transferred evidence
- **Change control**: a clear link from change requests ↔ implementation ↔ verification ↔ release notes
- **Role separation**: supplier produces and signs off; integrator verifies and accepts/rejects

Versioning & baselines
======================

Version policy
--------------

Use Semantic Versioning for shipped evidence bundles (e.g. ``1.4.0``), but keep in mind:

- A patch bump can still be safety-relevant if it changes behavior or evidence.
- Treat the version as a **baseline identifier** for audits.

Baseline content
----------------

A baseline should include, at least:

- documentation sources (RST/diagrams)
- implementation sources (if shipped)
- test sources and configuration
- generated evidence bundle (HTML output + machine-readable exports)
- toolchain metadata (versions, OS, compiler/interpreter, Sphinx and extensions)

Stable identifiers
------------------

IDs are contracts:

- keep ``REQ_*``, ``ARCH_*``, ``TEST_*`` stable across releases
- avoid reusing IDs for different intent (prefer deprecate + introduce)
- document renames/migrations explicitly

Change control
==============

Minimal process (recommended)
-----------------------------

1. **Change request**: capture the why/what (issue/ticket) and classify safety relevance.
2. **Impact analysis**: identify affected requirements, architecture, tests, and assumptions.
3. **Implementation**: commit changes with review.
4. **Verification**: run tests and regenerate evidence.
5. **Release notes**: update changelog with a safety-impact summary.
6. **Approval**: sign-off rules appropriate for integrity level.

Safety impact classification (practical)
----------------------------------------

Document each change as one of:

- **No safety impact** (formatting, typos, purely cosmetic docs)
- **Potential safety impact** (requirements wording, assumptions, interfaces, timing budgets)
- **Safety impact** (behavior change, threshold change, diagnostics, fail-safe logic)

For anything in the last two categories, require:

- explicit traceability updates
- verification updates (new/changed tests)
- updated shipment evidence

Configuration management
========================

What must be controlled
-----------------------

- Sphinx configuration (``conf.py``) and extension versions
- diagram sources (PlantUML) and rendering mode (local jar vs server)
- build scripts and CI workflows
- test harness (pytest/CMake/Cargo) and thresholds

How to keep builds reproducible
-------------------------------

- pin Python dependencies (Poetry lock or equivalent)
- keep build scripts deterministic (stable output paths, stable ordering)
- include exact tool versions in the shipment (or store alongside it)

Evidence bundle content & integrity
===================================

Expected files in a shipment directory
--------------------------------------

OSQAr treats a shipped evidence bundle as a directory that contains:

- Documentation (rendered HTML)
- ``needs.json`` (exported traceability graph)
- ``traceability_report.json`` (traceability check output)
- ``SHA256SUMS`` (checksum manifest for the directory)
- Raw test report XML (e.g. ``test_results.xml``)
- Coverage/analysis reports (e.g. coverage summary, complexity report)
- Implementation sources and tests (so evidence can be reviewed end-to-end)

Integrity workflow
------------------

Supplier side:

- generate ``SHA256SUMS`` inside the shipment directory
- verify it immediately after generation
- optionally sign the manifest externally (detached signature)

Integrator side:

- verify ``SHA256SUMS`` against the received directory
- reject intake if files are missing/mismatched

Supplier vs integrator workflows
================================

Supplier (produce + ship)
-------------------------

Recommended one-shot workflow (per shipment project)::

  ./osqar shipment prepare \
     --project <project_dir> \
     --clean \
     --archive

This performs:

- documentation build into the shipment directory (defaults to ``<project_dir>/_build/html`` unless you pass ``--shipment``)
- traceability export + validation
- checksum generation + verification
- optional archive creation (``.zip``)

Integrator (receive + verify)
-----------------------------

Recommended intake workflow::

  ./osqar shipment verify \
     --shipment /path/to/shipment \
     --traceability \
      --json-report /path/to/shipment/traceability_report.integrator.json \
      --report-json /path/to/shipment/verify_report.json

This performs:

- checksum verification
- optional traceability re-check into an integrator-side report

CI/CD integration (framework-level)
===================================

Recommended CI gates
--------------------

- build documentation for each shipped example/project
- run traceability checks (fail build on violations)
- generate checksums for the resulting shipment directory
- publish artifacts (HTML + JSON + manifests) as CI outputs

This OSQAr repository also demonstrates an end-to-end CI export of **deterministic example shipments** (C/C++/Rust) built with Bazel in reproducible mode, including test reports, full documentation builds, traceability reports, and checksum manifests.

Policy knobs
------------

- strictness of traceability rules (e.g. enforce REQ has TEST)
- whether tests are required to pass for a shipment to be valid
- whether archives are signed and how keys are managed

Handling external changes
=========================

Upstream tool changes
---------------------

Even if sources do not change, evidence output can change when:

- Sphinx or extensions change rendering
- PlantUML output changes
- test framework output format changes

Mitigations:

- pin dependencies
- treat tool upgrades as planned changes with explicit review
- regenerate and re-approve shipments after tool upgrades

Security & vulnerability response
=================================

For safety-related components, define a response policy:

- vulnerability intake and triage
- supported versions / maintenance windows
- patch release process and notification to integrators

Retention & archival
====================

Define retention expectations suitable for your domain:

- how long shipments are stored (years)
- where they are stored (immutable storage recommended)
- how access is controlled
- how to reproduce evidence from archived sources

Checklist summaries
===================

Supplier release checklist
--------------------------

- documentation builds cleanly
- traceability checks pass and report stored in shipment
- test reports stored (when applicable)
- ``SHA256SUMS`` generated and verified
- changelog updated with safety-impact summary
- archive created and transferred via controlled channel

Integrator intake checklist
---------------------------

- checksum verification passes
- traceability re-check passes (or deviations documented)
- assumptions reviewed and tracked
- integration tests planned/mapped to supplier requirements
- shipment archived with version and intake report
