Verification (ISO 26262-6 §9-§11 — ASIL D)
=============================================

This document specifies verification activities for the software safety
requirements and architectural design. The researched mapping in the OSQAr
reference catalog associates ISO 26262-6 Table 9 with software-unit structural
coverage. Exact percentages below are OSQAr project policy, pending tailoring
and review; they are not represented as thresholds prescribed by the standard.

Naming convention: ``VER_<CATEGORY>_<NNN>``.

.. note::
   Load ``iso26262-part6-software`` for ASIL-differentiated coverage targets
   and verification method selection tables.

Unit Testing
------------

.. ver:: Every safety-related function shall have unit tests covering
         nominal operation, boundary values, and all error paths.
         Tests shall be derived from the software safety requirements
         (not from the code).
   :id: VER_UNIT_001
   :status: draft
   :tags: ASIL_D;unit_test;requirements_based
   :links: REQ_SSR_NOMINAL_001;REQ_SSR_FAULT_001

Coverage — Statement
--------------------

.. ver:: Statement coverage shall be ≥100% for all safety-related
         source files. Any uncovered statements shall be justified
         as unreachable (defensive code after range checks, dead
         code guarded by compile-time constants).
   :id: VER_COVERAGE_STMT
   :status: draft
   :tags: ASIL_D;coverage;statement
   :links: REQ_SSR_NOMINAL_001;IMPL_SOURCE_INVENTORY

   **Tool:** gcov/lcov
   **Target:** Statement coverage ≥100%
   **Status:** Pending — run build-and-test.sh coverage

Coverage — Branch
-----------------

.. ver:: Branch coverage shall be ≥100% for all safety-related
         source files. Every conditional branch shall be exercised
         in both directions.
   :id: VER_COVERAGE_BRANCH
   :status: draft
   :tags: ASIL_D;coverage;branch
   :links: REQ_SSR_NOMINAL_001

   **Tool:** gcov/lcov (--branch-probabilities)
   **Target:** Branch coverage ≥100%

Coverage — MC/DC
----------------

.. ver:: Modified Condition/Decision Coverage (MC/DC) shall be
         demonstrated for all safety-related functions as an OSQAr
         project acceptance criterion. Table 9 is the researched
         software-unit structural-coverage reference.
   :id: VER_COVERAGE_MCDC
   :status: draft
   :tags: ASIL_D;coverage;MC/DC
   :links: REQ_SSR_FAULT_002;ARCH_DETERMINISTIC_FLOW

   **Tool:** gcov/lcov (--all-blocks for MC/DC approximation)
   **Target:** MC/DC coverage ≥100% with justified exclusions
   **Note:** gcov branch/block data is not treated as proof of MC/DC.
   The selected tool and any approximation require project justification
   and project-specific assessment.

Static Analysis — Coding Standard
---------------------------------

.. ver:: Static analysis shall enforce MISRA C:2012 (or AUTOSAR C++14)
         compliance for all safety-related source files. Zero mandatory
         rule violations. All required rule deviations shall be
         documented and justified.
   :id: VER_STATIC_MISRA
   :status: draft
   :tags: ASIL_D;static_analysis;MISRA_C;coding_standard
   :links: IMPL_SOURCE_INVENTORY

   **Tool:** cppcheck with MISRA addon (open-source approximation)
   **Target:** Zero violations of rules equivalent to MISRA mandatory
   **Status:** Pending

Static Analysis — Defects
-------------------------

.. ver:: Static analysis shall detect common defect patterns: buffer
         overruns, null pointer dereferences, use-after-free, resource
         leaks, uninitialized variables, and dead code.
   :id: VER_STATIC_DEFECTS
   :status: draft
   :tags: ASIL_D;static_analysis;defect_detection
   :links: REQ_SSR_FAULT_003;REQ_SSR_MEMORY_002

   **Tool:** cppcheck --enable=all, compiler warnings (-Werror -Wall -Wextra)
   **Target:** Zero warnings at maximum strictness

Dynamic Analysis — Memory Safety
---------------------------------

.. ver:: Dynamic analysis shall verify memory safety: no leaks, no
         use-after-free, no buffer overflows, no use of uninitialized
         memory. Test suite shall run under ASan (AddressSanitizer)
         and UBSan (UndefinedBehaviorSanitizer).
   :id: VER_DYNAMIC_MEMORY
   :status: draft
   :tags: ASIL_D;dynamic_analysis;ASan;UBSan;memory_safety
   :links: REQ_SSR_MEMORY_001;REQ_SSR_MEMORY_002

   **Tools:** GCC/Clang -fsanitize=address,undefined
   **Target:** Zero sanitizer findings

Dynamic Analysis — Valgrind
---------------------------

.. ver:: Valgrind Memcheck shall confirm zero memory errors across
         the full test suite, including unit tests and integration
         tests.
   :id: VER_DYNAMIC_VALGRIND
   :status: draft
   :tags: ASIL_D;valgrind;memcheck;memory_safety
   :links: VER_DYNAMIC_MEMORY

   **Tool:** Valgrind 3.22
   **Target:** Zero memory errors (0 bytes definitely lost,
   0 bytes indirectly lost, 0 errors)

Fuzzing
-------

.. ver:: A 24-hour (CPU time) fuzzing campaign shall be conducted
         against all external parsing/input interfaces with
         ASan+UBSan instrumentation. Zero crashes or memory errors
         tolerated.
   :id: VER_FUZZING
   :status: draft
   :tags: ASIL_D;fuzzing;AFLpp;robustness
   :links: REQ_SSR_NOMINAL_002;REQ_SSR_INTERFACE_001

   **Tool:** AFL++ 4.x
   **Duration:** 24 CPU-hours minimum
   **Target:** Zero crashes, zero sanitizer findings

Compiler Warning Audit
----------------------

.. ver:: The component shall compile with zero warnings under
         -Werror -Wall -Wextra -Wpedantic -Wconversion -Wshadow.
         Warning flags shall be documented in the build configuration.
   :id: VER_COMPILER_WARNINGS
   :status: draft
   :tags: ASIL_D;compiler;warnings;Werror
   :links: REQ_SSR_EXTASSUME_004

   **Configuration:** -Werror -Wall -Wextra -Wpedantic -Wconversion -Wshadow
   **Target:** Zero warnings

Reproducible Build
------------------

.. ver:: The component shall produce bit-identical builds when
         SOURCE_DATE_EPOCH is set to a fixed value, enabling
         independent verification of build outputs.
   :id: VER_REPRODUCIBLE
   :status: draft
   :tags: ASIL_D;reproducible_build;build_integrity
   :links: REQ_SSR_EXTASSUME_005

   **Method:** SOURCE_DATE_EPOCH=0 cmake --build build
   **Verification:** sha256sum across two independent rebuilds
