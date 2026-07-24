Verification Activities (ASIL D target)
==============================================

This document provides example verification activities for a project targeting
ASIL D. ISO 26262-6:2018 Clause 9 provides the software-unit verification
context. The activities below are draft project criteria, not completed
activities and not a claim that ISO 26262 qualification has been achieved.
Select concrete methods, tools, thresholds, and review criteria for the actual
language, product, and toolchain.

The packaged reference catalog associates ISO 26262-6:2018 Table 9 with
software-unit structural coverage. Exact percentages below are example project
policy pending tailoring and review; they are not represented as thresholds
prescribed by that table.

Unit testing
------------

.. ver:: Every safety-related function shall have requirements-based unit tests
         covering nominal operation, boundary values, and defined error paths.
   :id: VER_UNIT_001
   :status: draft
   :tags: ASIL_D;unit_test;requirements_based
   :links: REQ_SSR_NOMINAL_001;REQ_SSR_FAULT_001

Structural coverage — statement
-------------------------------

.. ver:: The project shall define, measure, and review statement coverage for
         safety-related source files. Uncovered statements shall be justified.
   :id: VER_COVERAGE_STMT
   :status: draft
   :tags: ASIL_D;coverage;statement;project_policy
   :links: REQ_SSR_NOMINAL_001;IMPL_SOURCE_INVENTORY

   **Example target:** 100%, pending project authorization.
   **Evidence state:** Pending; no measurement is asserted.

Structural coverage — branch
----------------------------

.. ver:: The project shall define, measure, and review branch coverage for
         safety-related source files, including treatment of infeasible paths.
   :id: VER_COVERAGE_BRANCH
   :status: draft
   :tags: ASIL_D;coverage;branch;project_policy
   :links: REQ_SSR_NOMINAL_001

   **Example target:** 100%, pending project authorization.
   **Evidence state:** Pending; no measurement is asserted.

Structural coverage — MC/DC
---------------------------

.. ver:: The project shall select a suitable method and evidence source for
         MC/DC where the project's applicability analysis requires it.
   :id: VER_COVERAGE_MCDC
   :status: draft
   :tags: ASIL_D;coverage;MC/DC;project_policy
   :links: REQ_SSR_FAULT_002;ARCH_DETERMINISTIC_FLOW

   **Example target:** 100% with reviewed exclusions, pending authorization.
   Branch or block coverage from a general-purpose coverage tool is not treated
   as proof of MC/DC.

Coding-standard analysis
------------------------

.. ver:: The project shall identify an applicable language coding standard,
         analyze safety-related source files against the selected rules, and
         review violations and deviations.
   :id: VER_STATIC_CODING_STANDARD
   :status: draft
   :tags: ASIL_D;static_analysis;coding_standard
   :links: IMPL_SOURCE_INVENTORY

   **Method and acceptance criteria:** Project-specific and pending.

Defect-oriented analysis
------------------------

.. ver:: Static and dynamic analyses shall address defect classes relevant to
         the selected language, interfaces, compiler, and execution environment.
   :id: VER_STATIC_DEFECTS
   :status: draft
   :tags: ASIL_D;analysis;defect_detection
   :links: REQ_SSR_MEMORY_002

   **Method and acceptance criteria:** Project-specific and pending.

Memory and resource behavior
----------------------------

.. ver:: The project shall verify memory and resource behavior against the
         authored requirements and architecture using methods suitable for the
         selected language and target environment.
   :id: VER_DYNAMIC_MEMORY
   :status: draft
   :tags: ASIL_D;dynamic_analysis;memory_safety;resource_usage
   :links: REQ_SSR_MEMORY_001;REQ_SSR_MEMORY_002

Fuzzing
-------

.. ver:: The project shall define a robustness or fuzzing campaign for exposed
         input interfaces, including duration, instrumentation, corpus, and
         acceptance criteria.
   :id: VER_FUZZING
   :status: draft
   :tags: ASIL_D;fuzzing;robustness;project_policy
   :links: REQ_SSR_NOMINAL_002;REQ_SSR_INTERFACE_001

   **Example duration:** 24 CPU-hours, pending project authorization.

Compiler diagnostics
--------------------

.. ver:: The project shall document enabled compiler diagnostics and resolve or
         review every diagnostic produced by the accepted build configuration.
   :id: VER_COMPILER_WARNINGS
   :status: draft
   :tags: ASIL_D;compiler;diagnostics
   :links: REQ_SSR_EXTASSUME_004;IMPL_BUILD_CONFIG

Reproducible build
------------------

.. ver:: The project shall define and evaluate a reproducible-build criterion
         suitable for its build system and delivered artifacts.
   :id: VER_REPRODUCIBLE
   :status: draft
   :tags: ASIL_D;reproducible_build;build_integrity
   :links: REQ_SSR_EXTASSUME_005

   **Method and acceptance criteria:** Project-specific and pending.
