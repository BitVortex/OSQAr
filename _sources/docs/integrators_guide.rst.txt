==================
Integrator’s Guide
==================

If you are new to OSQAr, start with :doc:`using_the_boilerplate` and :doc:`project_setup_from_scratch`.

See also: :doc:`multi_project_workflows` for batch intake and multi-shipment verification patterns.

Scope
=====

This guide is for the **integrator** of a Safety Element out of Context (SEooC):

- you integrate a reusable component into a product/system with specific context
- you assign domain-specific integrity levels and complete the safety case

For a full CLI command/option reference, see :doc:`cli_reference`.

OSQAr helps you verify and intake auditable evidence shipments (and keep the traceability chain consistent), but it does not replace system engineering or certification.

Integrator responsibilities (checklist)
=======================================

Assumptions and context
-----------------------

- Define the intended use and operational context.
- Identify supplier assumptions; validate them in your system.

Hazard analysis and integrity assignment
----------------------------------------

- Perform domain-appropriate hazard analysis (HARA/HAZOP/FMEA as applicable).
- Assign integrity levels (ASIL/SIL/PL or equivalent) in context.
- Derive system-level safety goals and requirements.

Interface and configuration control
-----------------------------------

- Define interface contracts (signals, timing, units, error behavior).
- Freeze and change-control safety-relevant parameters.

Verification strategy
---------------------

- Ensure each safety requirement is verified by at least one method:

  - analysis
  - review/inspection
  - test (unit, integration, system)

- Extend verification beyond unit tests:

  - integration tests (interfaces, timing, fault handling)
  - environmental tests (noise profiles, operating extremes)
  - fault injection (if required by integrity level)

Evidence packaging
------------------

- Archive evidence that an assessor can reproduce:

  - rendered HTML documentation
  - requirement and traceability artifacts
  - test results (e.g., JUnit XML)
  - tool versions and environment description

Integrity verification of a supplier shipment
---------------------------------------------

Treat each **example build output directory** you receive from a supplier as a controlled software shipment.
The supplier should provide a checksum manifest file ``SHA256SUMS`` at the root of that shipment.

Recommended integrator procedure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Unpack the shipment into a controlled location.

2. Verify the checksum manifest using the OSQAr checksum tool::

      ./osqar checksum verify \
        --root /path/to/shipment \
        --manifest /path/to/shipment/SHA256SUMS

   Recommended integrator one-shot workflow (CLI)::

      ./osqar shipment verify \
        --shipment /path/to/shipment \
        --traceability \
        --json-report /path/to/shipment/traceability_report.integrator.json \
        --report-json /path/to/shipment/verify_report.json

    Optional extensions:

    - Use ``--verify-command '<cmd>'`` (repeatable) to run additional integrator-side checks after OSQAr’s built-in verification.
    - Use ``--config-root <dir>`` / ``--config <path>`` to load a trusted integrator workspace config (``osqar_workspace.json``).
    - Disable hooks via ``--no-hooks`` or by setting ``OSQAR_DISABLE_HOOKS=1``.

   - If verification reports ``missing`` or ``mismatched`` files, treat the shipment as corrupted or tampered
     with, and re-transfer the artifact.
   - Do not regenerate ``SHA256SUMS`` on the receiver side as a substitute for verification.

3. Verify traceability artifacts (machine-readable) as part of intake:

   - ``needs.json``: the exported traceability graph
   - ``traceability_report.json``: the supplier's check result

   You can re-run the checks locally to confirm the shipment content passes your intake gate::

      ./osqar traceability /path/to/shipment/needs.json \
        --json-report /path/to/shipment/traceability_report.integrator.json

   Store your integrator-side report alongside the shipped evidence.

Multi-shipment intake (recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you routinely integrate multiple supplier projects, archive them using the workspace intake command.
This produces a single dated intake folder with a **Subproject overview** summary file::

      ./osqar workspace intake \
        --root intake/received \
        --recursive \
        --output intake/archive/2026-02-01 \
        --traceability

For a quick, non-copying inventory of received shipments, you can also use::

  ./osqar workspace report --root intake/received --recursive --output intake/overview --open

How to tailor the reference example
===================================

- Copy the chapter structure and replace content with system-specific artifacts.
- Add integration requirements and link them into the chain (REQ ↔ ARCH ↔ TEST).
- Add system diagrams showing the SEooC boundary and external dependencies.
- Add integration/system ``TEST_*`` needs and link them to affected requirements.

Review questions
================

- Which assumptions are safety-relevant, and how are they validated?
- Are safety-related configuration values protected and change-controlled?
- Do timing budgets hold under worst-case conditions?
- Is traceability complete and bidirectional (REQ ↔ ARCH ↔ TEST)?
