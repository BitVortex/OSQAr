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

Example commands (supplier, docs-only update)::

  ./osqar build-docs --project examples/python_hello_world
  ./osqar shipment checksums --shipment examples/python_hello_world/_build/html generate
  ./osqar shipment checksums --shipment examples/python_hello_world/_build/html verify

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

Example commands (supplier, requirement change)::

  ./osqar supplier prepare \
     --project examples/python_hello_world \
     --clean \
     --archive

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

Example commands (supplier, implementation change)::

  ./osqar supplier prepare \
     --project examples/python_hello_world \
     --clean \
     --archive

Toolchain changes
-----------------

Examples:

- upgrading Sphinx / sphinx-needs
- changing PlantUML rendering mode

Actions:

- treat as planned change
- rebuild and compare outputs
- re-approve evidence baseline

Multi-language note
===================

This TSIM example exists in multiple implementation languages.
To keep lifecycle management consistent:

- keep the requirements and verification intent in the shared TSIM docs
- keep language-specific implementation details in each example's implementation chapter
- keep test IDs (``TEST_*``) stable even if underlying test framework differs

Notes and pitfalls
==================

- Treat shipped HTML outputs as **immutable evidence**. If anything changes, create a new shipment.
- Integrators should **verify** manifests, not regenerate them (regeneration defeats integrity checks).
- Keep IDs stable (``REQ_*``, ``ARCH_*``, ``TEST_*``). If you truly must replace an ID, document the mapping.
- Prefer additive changes over rewrites; it makes diffs reviewable and reduces merge conflicts.

Worked example (requirement change)
===================================

Scenario:

- You tighten a threshold in a ``REQ_*`` need.

Minimum actions:

1. Update the requirement text and any assumptions.
2. Update trace links (REQ ↔ ARCH ↔ TEST) if they no longer match.
3. Update tests (or add a new test) and ensure the test ID remains stable.
4. Run the end-to-end example workflow (tests → docs import → shipment integrity):

   - Run the example's ``build-and-test.sh`` (if present).
   - Rebuild docs.
   - Re-run traceability checks.
   - Regenerate checksums.

Supplier workflow (produce shipment)
====================================

From the repository root (recommended)::

  ./osqar supplier prepare \
     --project examples/python_hello_world \
     --clean \
     --archive

Notes:

- By default, OSQAr will run the example's ``build-and-test.sh`` *if it exists*.
  Use ``--skip-tests`` to force skipping.
- The shipment directory defaults to ``<project>/_build/html``.

Optional: add supplier metadata to the shipment root (helps integrator intake)::

  ./osqar shipment metadata write \
     --shipment examples/python_hello_world/_build/html \
     --name "TSIM (Python)" \
     --version "<your_version>" \
     --url repository=https://example.com/repo.git \
     --origin url=https://example.com/repo.git \
     --origin revision=<commit>

Integrator workflow (verify shipment)
=====================================

After unpacking a received shipment::

  ./osqar integrator verify \
     --shipment /path/to/shipment \
     --traceability

If you intake multiple shipments at once, prefer the batch workflow::

  ./osqar workspace intake \
     --root /path/to/received \
     --recursive \
     --output /path/to/archive/<date> \
     --traceability

Archiving and traceability continuity
=====================================

- Archive the shipment directory (or a signed archive) per version.
- Keep need IDs stable; stable IDs make diffs and intake reviews possible.
- If an ID must be replaced, document the mapping (old ↔ new) in release notes.

