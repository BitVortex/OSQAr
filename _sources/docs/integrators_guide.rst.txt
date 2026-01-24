==================
Integrator’s Guide
==================

Scope
=====

This guide is for the **integrator** of a Safety Element out of Context (SEooC):

- you integrate a reusable component into a product/system with specific context
- you assign domain-specific integrity levels and complete the safety case

OSQAr helps keep the traceability chain consistent, but it does not replace system engineering or certification.

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
