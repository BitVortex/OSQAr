Bounded Standards-Claim Examples
================================

Boundary of these examples
--------------------------

ISO 26262 is only the example catalog shipped with this template; other
catalogs can use stable ``reference_id`` values. Links are mechanical only:
they show authored project relationships and do not assess the correctness of
an interpretation or the adequacy of support. This base template records no
organization-specific disposition. The examples are deliberately incomplete
and do not establish compliance, qualification, certification, or safety.
Project-authorized review must determine applicability, interpretation, and
evidence sufficiency.

The evidence placeholders remain pending. They do not assert executions,
results, provenance, review, or acceptance. General-purpose branch or block
coverage data is not proof of MC/DC.

Selected software-requirements context
--------------------------------------

.. stdclaim:: Selected software safety requirements activities
   :id: STDCLAIM_SW_REQUIREMENTS
   :status: draft
   :standards_catalog: iso26262-2018
   :standards_refs: ISO26262-6:2018-C6.4.1
   :project_interpretation: This project treats requirements specification as a lifecycle activity; VER_UNIT_001 evaluates selected project requirements, but one activity does not prove the complete cited context.
   :applicability: Draft software safety requirements for this example SEooC.
   :realized_by: REQ_SSR_NOMINAL_001;REQ_SSR_FAULT_001;REQ_SSR_MEMORY_001
   :verified_by: VER_UNIT_001

   This draft claim covers only the linked example requirements and activity.
   It does not claim that one activity verifies all expectations associated
   with ISO 26262-6:2018 Clause 6.4.1.

Project structural-coverage criterion
-------------------------------------

.. stdclaim:: Project structural-coverage criterion and activities
   :id: STDCLAIM_STRUCTURAL_COVERAGE
   :status: draft
   :standards_catalog: iso26262-2018
   :standards_refs: ISO26262-6:2018-T9
   :project_interpretation: ISO 26262-6:2018 Table 9 is used here as a normative recommendation for structural coverage; the exact percentage thresholds are project policy, not thresholds prescribed by the cited table.
   :applicability: Draft software-unit structural-coverage criteria for safety-related source files.
   :realized_by: REQ_VER_COVERAGE_CRITERIA
   :verified_by: VER_COVERAGE_STMT;VER_COVERAGE_BRANCH;VER_COVERAGE_MCDC
   :evidenced_by: EVID_COVERAGE_REPORT

   The pending report does not demonstrate that the activities ran or that
   the project criterion was met. General branch or block coverage is not
   proof of MC/DC; a suitable project method and review remain necessary.

Selected SEooC assumptions-of-use guidance
------------------------------------------

.. stdclaim:: Selected SEooC assumptions of use
   :id: STDCLAIM_SEOOC_AOU
   :status: draft
   :standards_catalog: iso26262-2018
   :standards_refs: ISO26262-10:2018-C9
   :project_interpretation: ISO 26262-10:2018 Clause 9 is guidance for this project's selected SEooC assumptions of use; the linked lifecycle records are project-authored assumptions.
   :applicability: Draft integration assumptions for this example SEooC.
   :realized_by: LM_AOU_INTEGRATION;LM_AOU_INPUTS;LM_AOU_THREADING;LM_AOU_ERROR_HANDLING

   This guidance example intentionally has no verification or evidence link.
