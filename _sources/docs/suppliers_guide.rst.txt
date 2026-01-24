================
Supplier’s Guide
================

Scope
=====

This guide is for a **supplier** shipping a component/SEooC together with compliance-ready documentation.

The goal is to provide a package that allows an integrator to:

- understand intended use and limitations
- reuse evidence where appropriate
- complete context-specific safety analysis and verification

Supplier deliverables
=====================

Documentation deliverables
--------------------------

Provide a structured documentation set:

- safety goals and safety requirements (``REQ_SAFETY_*``)
- functional requirements (``REQ_FUNC_*``)
- architecture/design constraints (``ARCH_*``)
- verification requirements and methods (``TEST_*``)
- traceability matrices demonstrating coverage

Operational assumptions (critical)
----------------------------------

Document assumptions clearly:

- environment ranges (temperature, vibration, EMC/noise)
- sampling rates, timing budgets, scheduling assumptions
- sensor characteristics and calibration assumptions
- expected failure modes and diagnostic coverage boundaries

Interface specification
-----------------------

Provide stable interface definitions:

- signal names, units, ranges, validity rules
- error reporting behavior
- initialization and degraded mode behavior
- timing constraints and performance limits

Verification artifacts
----------------------

Provide machine-readable test output when possible (e.g., JUnit XML), and record tool versions/configuration.

Change control and versioning
=============================

Version the supplier package and include:

- a changelog describing safety-impacting changes
- compatibility notes (interfaces, configuration)
- migration guidance for integrators

How to use OSQAr as a supplier
==============================

- Start from the reference chapter structure and keep it consistent.
- Treat requirement IDs as a contract; keep them stable across releases.
- Provide review-friendly traceability with both ``:links:`` and explicit tables.
- Ship an evidence bundle (rendered HTML, sources, diagrams, test outputs, toolchain metadata).

Integrator handoff
==================

Clarify:

- intended use and out-of-scope behavior
- assumptions that must be validated during integration
- safety-relevant configuration parameters
- what evidence is reusable vs must be redone in context
