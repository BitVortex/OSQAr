Lifecycle Management (ISO 26262 Parts 2,8,10)
===============================================

Assumptions of Use, configuration management baseline, tool qualification,
and safety case evidence index for the ASIL D SEooC qualification attempt.

Naming convention: ``LM_<CATEGORY>_<NNN>``.

.. note::
   Load ``iso26262-part6-software`` and ``compliance-documentation``
   for guidance on lifecycle management content.

Assumptions of Use (SEooC — general guidance in ISO 26262-10 §9.1)
------------------------------------------------------------------

.. lm:: **Integration context**: The software component assumes
       single-threaded execution or externally-synchronized
       multi-threaded access. Integration into a preemptive
       multi-tasking environment requires external mutual exclusion.
   :id: LM_AOU_INTEGRATION
   :status: draft
   :tags: ASIL_D;SEooC;assumption_of_use;integration
   :links: REQ_SSR_EXTASSUME_001

.. lm:: **Input constraints**: All inputs are assumed to be
       pre-validated for physical integrity by hardware diagnostics
       or a higher-level safety mechanism. The component validates
       logical integrity (range, type, structure).
   :id: LM_AOU_INPUTS
   :status: draft
   :tags: ASIL_D;SEooC;assumption_of_use;input_validation
   :links: REQ_SSR_EXTASSUME_002

.. lm:: **Threading model**: The component is designed for
       single-threaded use. The integrator shall ensure that no
       function is called reentrantly unless explicitly documented
       as reentrant-safe. No internal state is shared between
       instances without explicit synchronization.
   :id: LM_AOU_THREADING
   :status: draft
   :tags: ASIL_D;SEooC;assumption_of_use;threading
   :links: REQ_SSR_EXTASSUME_001

.. lm:: **Error handling**: The integrator shall implement a
       system-level fault reaction that responds to each error
       code returned by the component. Error codes mapped to
       system-level responses shall be documented.
   :id: LM_AOU_ERROR_HANDLING
   :status: draft
   :tags: ASIL_D;SEooC;assumption_of_use;error_handling
   :links: REQ_SSR_EXTASSUME_003

.. lm:: **Toolchain**: The component shall be compiled using the compiler
       version and build configuration covered by this project's reviewed
       tool-use analysis. Classification and any qualification action shall
       be determined for the actual use case under ISO 26262-8 Clause 11.
   :id: LM_AOU_TOOLCHAIN
   :status: draft
   :tags: ASIL_D;SEooC;assumption_of_use;toolchain
   :links: REQ_SSR_EXTASSUME_004;IMPL_BUILD_CONFIG

Configuration Management Baseline
----------------------------------

.. lm:: Configuration baseline at qualification release.
       All safety artifacts under version control in the
       qualification repository.
   :id: LM_CM_BASELINE
   :status: draft
   :tags: ASIL_D;configuration_management;baseline

   **Repository tag:** <libversion>-<osqarversion>
   **Artifacts:** 01-06 RST documents, conf.py, osqar_project.json,
   source code, build configuration, verification evidence
   **Retention:** <project retention period and organizational-policy basis>

Tool Qualification
------------------

.. lm:: Project-specific confidence analysis for each relied-upon tool use
       under ISO 26262-8 Clause 11.
   :id: LM_TOOL_TCL
   :status: draft
   :tags: ASIL_D;tool_qualification;TCL

   **Compiler (GCC):** <use case, impact, error-detection measures,
   reviewed classification, and any qualification action>
   **Static analyzer (cppcheck):** <project-specific evaluation>
   **Coverage tool (gcov/lcov):** <project-specific evaluation>
   **Build system (CMake):** <project-specific evaluation>

   Tool names and categories do not determine fixed TI/TD/TCL results. Complete
   this analysis for the project's actual uses before claiming tool confidence
   or qualification.

Safety Case Evidence Index
--------------------------

.. lm:: Evidence index mapping safety case claims to verification
       evidence artifacts.
   :id: LM_EVIDENCE_INDEX
   :status: draft
   :tags: ASIL_D;safety_case;evidence_index

   **SC_SAFETY_PARSE (parsing safety) →** VER_UNIT_001, VER_FUZZING
   **SC_SAFETY_MEMORY (memory safety) →** VER_DYNAMIC_MEMORY, VER_DYNAMIC_VALGRIND
   **SC_SAFETY_ARITHMETIC (arithmetic safety) →** VER_COVERAGE_MCDC
   **SC_SAFETY_VERIFICATION (verification completeness) →**
   VER_COVERAGE_STMT, VER_COVERAGE_BRANCH, VER_STATIC_MISRA,
   VER_STATIC_DEFECTS, VER_REPRODUCIBLE
