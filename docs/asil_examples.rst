Understanding the ASIL-Target Examples
======================================

OSQAr packages two examples for learning how an evidence model can be organized
when a project **targets ASIL D**:

* ``asil_example_c`` — a small C library built with CMake;
* ``asil_example_rust`` — a small Rust library built with Cargo.

They are examples, not qualified components. Creating, compiling, testing, or
rendering either example does not establish ASIL qualification, ISO 26262
compliance, certification, or safety.

Prerequisites
=============

OSQAr does not install native C or Rust toolchains. Before using an example,
confirm the corresponding commands are available:

* C: ``cc --version``, ``cmake --version``, and ``ctest --version``;
* Rust: ``rustc --version`` and ``cargo --version``.

Use toolchain versions selected and controlled by your project. The checks above
only establish command availability, not suitability for safety-related use.

Create an example
=================

C::

   osqar new --language c --template asil_example_c --name asil_c_walkthrough
   cd asil_c_walkthrough
   ./build-and-test.sh test
   osqar build-docs

Rust::

   osqar new --language rust --template asil_example_rust --name asil_rust_walkthrough
   cd asil_rust_walkthrough
   ./build-and-test.sh test
   osqar build-docs

The template name and ``--language`` must match. OSQAr rejects a C/Rust mismatch
before creating the destination.

What both examples demonstrate
==============================

The examples share one language-neutral evidence narrative:

``00_standards_claims.rst``
   Three bounded ``STDCLAIM_*`` records demonstrate authored
   ``realized_by``, ``verified_by``, and ``evidenced_by`` links. The packaged
   ISO 26262 catalog and interpretations are illustrative.

``01_requirements.rst``
   Draft project requirements and assumptions tagged with the target integrity
   level. Tags communicate project intent; they do not prove satisfaction.

``02_architecture.rst``
   Draft architecture linked to selected requirements.

``03_verification.rst``
   Planned activities with project-policy examples. Concrete methods, tools,
   thresholds, exclusions, and acceptance criteria remain project decisions.

``05_test_results.rst``
   Explicitly pending evidence placeholders. A source test run is not silently
   promoted into accepted qualification evidence.

``06_lifecycle_management.rst``
   Draft assumptions of use, baseline prompts, and tool-use-analysis prompts.

Each language directory overlays its own implementation page, source, tests,
build script, Sphinx configuration, README, and ``osqar_project.json``.

C and Rust are intentionally different
======================================

The C example demonstrates a C11 library, explicit error codes, CMake/CTest,
and C-oriented analysis placeholders. These are example project choices, not
requirements attributed directly to ISO 26262.

The Rust example demonstrates safe checked arithmetic, a small stateful API,
Cargo tests, and a prohibition on unsafe Rust in the example crate. It does not
claim that Rust language properties eliminate project hazards, verification
needs, compiler reliance, runtime assumptions, or integration obligations.

The shared documentation avoids prescribing C-only tools or coding standards to
the Rust example. Language-specific tool and coding-rule choices belong in each
project's implementation, verification, and tool-use analyses.

Follow the exemplary links
==========================

After building the docs, export and check the authored graph::

   osqar traceability _build/html/needs.json \
     --project-config osqar_project.json \
     --json-report _build/html/traceability_report.json

The untouched examples intentionally return nonzero because several draft
requirements lack architecture links. The violations are a visible tailoring
queue, not accepted deviations. After resolving them, a passing basic report
would mean only that the executed mechanical rules passed; it would not show
that an interpretation is correct, an activity ran, or evidence was accepted.
For strict qualification-profile behavior and authoritative evidence
acceptance, see :doc:`typed_traceability` and :doc:`evidence_acceptance`.

Tailoring checklist
===================

Before using either example in a project:

#. Replace the illustrative catalog declaration with project-authorized sources.
#. Review or remove every ``STDCLAIM_*`` interpretation and applicability field.
#. Derive project requirements from the actual safety concept and interfaces.
#. Replace example architecture and assumptions with the implemented design and
   integration contract.
#. Select language- and target-appropriate verification methods and criteria.
#. Pin and assess relied-upon compiler, build, analysis, and evidence tools.
#. Generate evidence with provenance; do not hand-write passing results.
#. Apply independent review and the project's acceptance authority.
#. Preserve accepted outputs and exact inputs in the released shipment.

For command details, continue with :doc:`cli_reference`. For project creation
and migration guidance, see :doc:`project_setup_from_scratch`.
