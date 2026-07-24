Lifecycle and Assumptions
=========================

This page contains draft assumptions of use and lifecycle records for an
example SEooC project targeting ASIL D. ISO 26262-6:2018 Clause 10 provides
software-integration and verification context, while ISO 26262-6:2018 Clause 11
provides embedded-software testing context. The records below are prompts for
project tailoring, not accepted assumptions, a completed safety case, or
qualification evidence.

Assumptions of use
------------------

.. lm:: **Integration context**: The software component assumes
       single-threaded execution or externally synchronized concurrent access.
       The integrator shall define synchronization and scheduling constraints.
   :id: LM_AOU_INTEGRATION
   :status: draft
   :tags: ASIL_D;SEooC;assumption_of_use;integration
   :links: REQ_SSR_EXTASSUME_001

.. lm:: **Input constraints**: The integrator shall define which physical and
       communication-integrity checks occur outside the component and which
       logical validation remains inside it.
   :id: LM_AOU_INPUTS
   :status: draft
   :tags: ASIL_D;SEooC;assumption_of_use;input_validation
   :links: REQ_SSR_EXTASSUME_002

.. lm:: **Threading model**: The integrator shall prevent unsupported reentrant
       calls and shall document ownership of mutable state.
   :id: LM_AOU_THREADING
   :status: draft
   :tags: ASIL_D;SEooC;assumption_of_use;threading
   :links: REQ_SSR_EXTASSUME_001

.. lm:: **Error handling**: The integrator shall map component errors to
       reviewed system-level responses.
   :id: LM_AOU_ERROR_HANDLING
   :status: draft
   :tags: ASIL_D;SEooC;assumption_of_use;error_handling
   :links: REQ_SSR_EXTASSUME_003

.. lm:: **Toolchain**: The component shall be built with the compiler, build
       configuration, and supporting tools covered by the project's reviewed
       tool-use analysis. Classification and any qualification action shall be
       determined for the actual use case under ISO 26262-8:2018 Clause 11.
   :id: LM_AOU_TOOLCHAIN
   :status: draft
   :tags: ASIL_D;SEooC;assumption_of_use;toolchain
   :links: REQ_SSR_EXTASSUME_004;IMPL_BUILD_CONFIG

Configuration-management baseline
---------------------------------

.. lm:: The project shall define a controlled baseline containing authored
       needs, implementation, build configuration, verification plans, and
       generated evidence with explicit provenance.
   :id: LM_CM_BASELINE
   :status: draft
   :tags: ASIL_D;configuration_management;baseline

   **Repository tag:** Replace with the project's accepted baseline identifier.
   **Retention:** Replace with project and organizational policy.

Tool-use analysis
-----------------

.. lm:: The project shall assess each relied-upon tool use under its applicable
       process and ISO 26262-8:2018 Clause 11 context.
   :id: LM_TOOL_TCL
   :status: draft
   :tags: ASIL_D;tool_qualification;TCL

   Tool names or categories do not determine fixed TI, TD, or TCL results.
   Record the actual use, possible impact, detection measures, reviewed
   classification, and any required qualification action.

Evidence index
--------------

.. lm:: The project shall maintain a reviewed mapping from assurance claims to
       accepted verification evidence.
   :id: LM_EVIDENCE_INDEX
   :status: draft
   :tags: ASIL_D;safety_case;evidence_index

   This example intentionally contains only pending links and does not establish
   that evidence is sufficient or accepted.
