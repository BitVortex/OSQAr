====================
Lifecycle Management
====================

Purpose
=======

This chapter explains how to manage the TSIM example through its lifecycle:

- requirements evolution
- implementation changes across languages
- verification and evidence regeneration
- supplier shipment creation and integrator intake

Even though this is a reference example, the workflow is intentionally close to real-world safety projects.

What is a "shipment" in this example?
=====================================

For this example, the **shipment** is the Sphinx HTML output directory:

- ``<example>/_build/html``

It should contain the full evidence set an assessor would want to inspect.

Minimum expected artifacts
--------------------------

Inside the shipped directory:

- ``needs.json`` (sphinx-needs export)
- ``traceability_report.json`` (OSQAr traceability check)
- ``SHA256SUMS`` (checksum manifest)
- raw test output XML (when available), e.g. ``test_results.xml``

Change scenarios and required actions
=====================================

This table is intentionally conservative.

Documentation-only changes
--------------------------

Examples:

- typos in explanatory text
- reformatting sections

Actions:

- rebuild docs
- regenerate checksums

Requirement changes
-------------------

Examples:

- change thresholds, timing budgets, or assumptions
- add/modify ``REQ_*`` needs

Actions:

- update trace links (REQ ↔ ARCH ↔ TEST)
- update verification chapter and tests
- rebuild docs
- re-run traceability checks
- regenerate checksums

Implementation changes
----------------------

Examples:

- change conversion/filter logic
- change alert thresholds or hysteresis

Actions:

- run the example's end-to-end script (tests ↔ docs)
- ensure JUnit XML is produced
- rebuild docs (to import new test results)
- re-run traceability and checksums

Toolchain changes
-----------------

Examples:

- upgrading Sphinx / sphinx-needs
- changing PlantUML rendering mode

Actions:

- treat as planned change
- rebuild and compare outputs
- re-approve evidence baseline

Recommended workflows
=====================

Supplier workflow (produce shipment)
------------------------------------

From the repository root (recommended)::

   poetry run python -m tools.osqar_cli supplier prepare \
     --project examples/python_hello_world \
     --clean

Notes:

- Use the matching example directory (C/C++/Rust/Python) as ``--project``.
- If the example includes a ``build-and-test.sh``, you can omit ``--skip-tests`` to run it.

Integrator workflow (verify shipment)
-------------------------------------

After unpacking a received shipment::

   poetry run python -m tools.osqar_cli integrator verify \
     --shipment /path/to/shipment \
     --traceability

Archiving and traceability continuity
=====================================

- Archive the shipment directory (or a signed archive) per version.
- Keep need IDs stable; stable IDs make diffs and intake reviews possible.
- If an ID must be replaced, document the mapping (old ↔ new) in release notes.

Multi-language note
===================

This TSIM example exists in multiple implementation languages.
To keep lifecycle management consistent:

- keep the requirements and verification intent in the shared TSIM docs
- keep language-specific implementation details in each example's implementation chapter
- keep test IDs (``TEST_*``) stable even if underlying test framework differs
Implementation changes

Examples:


Actions:


Toolchain changes

Examples:


Actions:


Recommended workflows
=====================

Supplier workflow (produce shipment)

From the repository root (recommended)::

   poetry run python -m tools.osqar_cli supplier prepare \
     --project examples/python_hello_world \
     --clean

Notes:


Integrator workflow (verify shipment)

After unpacking a received shipment::

   poetry run python -m tools.osqar_cli integrator verify \
     --shipment /path/to/shipment \
     --traceability

Archiving and traceability continuity
=====================================


Multi-language note
===================

This TSIM example exists in multiple implementation languages.
To keep lifecycle management consistent:


Supplier workflow (produce shipment)
------------------------------------

