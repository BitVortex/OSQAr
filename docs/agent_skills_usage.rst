.. _agent-skills-usage:

Agent Skills for OSQAr Qualification
####################################

OSQAr ships with a set of **content-authoring skills** in ``skills/`` that help
authors map ISO standards requirements onto OSQAr qualification needs. These are
designed to be used by both human engineers and AI agents (LLMs).

This guide explains how agents should navigate the full OSQAr skill ecosystem —
both the in-repository content-authoring skills and the research profile's domain
knowledge skills.

.. note::
   **Human Responsibility**: All LLM-generated qualification content MUST be
   reviewed and approved by a competent functional safety engineer before
   inclusion in any qualification baseline. See ``skills/README.md`` for the
   full disclaimer on LLM usage in safety-critical contexts.

Two-Tier Skill Architecture
===========================

OSQAr skills operate in two complementary tiers:

.. list-table:: Skill Tiers
   :header-rows: 1

   * - Tier
     - Location
     - Content
     - Examples
   * - **Content-Authoring** (in-repo)
     - ``OSQAr/skills/``
     - How to write OSQAr RST needs, ASIL-differentiated guidance, concrete examples
     - ``iso26262-part6-software``, ``iso26262-part5-hardware``, ``security-coengineering``
   * - **Research Skills** (agent profile)
     - Agent's research skill set
     - Deep domain knowledge: clause-level requirements, hazard analysis methods, standard cross-referencing
     - ``iso-26262-application`` (65 clause requirements), ``hazard-analysis-methods``, ``functional-safety-fundamentals``

**When assisting with qualification, agents should load BOTH tiers**: research skills
provide the domain expertise; content-authoring skills provide the OSQAr-specific mapping.

Available Content-Authoring Skills (In-Repo)
============================================

.. list-table::
   :header-rows: 1
   :widths: 25, 55, 20

   * - Skill
     - Use When
     - Primary Standards
   * - ``iso26262-part6-software``
     - Authoring software safety requirements, architecture, verification for C/C++/Rust libraries
     - ISO 26262-6
   * - ``security-coengineering``
     - Adding cybersecurity (TARA, CAL, UN R155) to an existing safety qualification
     - ISO/SAE 21434
   * - ``sotif-qualification``
     - Qualifying ADAS/autonomous functions — sensor limitations, triggering events, scenario validation
     - ISO 21448
   * - ``vehicle-program-qualification``
     - Scaling qualification to multi-ECU, multi-supplier vehicle programs with DIA management
     - ISO 26262 Parts 2,4,7,8,10
   * - ``compliance-documentation``
     - Generating audit-ready traceability matrices, gap analyses, evidence indices, assessment checklists
     - ISO 26262, 21434, 21448

Qualification Task → Skill Routing
===================================

**Step 1: Identify the task scope.** What are you qualifying?

* **A C library** (like cJSON) → ``iso26262-part6-software``
* **A connected ECU** (safety + cybersecurity) → ``iso26262-part6-software`` + ``security-coengineering``
* **ADAS perception** (safety + SOTIF) → ``iso26262-part6-software`` + ``sotif-qualification``
* **A full vehicle program** → ``vehicle-program-qualification`` (which orchestrates the others)
* **Preparing for assessment** → ``compliance-documentation``

**Step 2: Load the content-authoring skill.** This gives you need ID conventions,
ASIL-differentiated guidance, RST examples, and pitfalls specific to OSQAr.

**Step 3: Load the research skill for clause-level backing.** For example:

* Working on software → also load ``iso-26262-application`` (Part 6 sections)
* Need FMEA/FTA → also load ``hazard-analysis-methods``
* Cross-domain question → also load ``functional-safety-fundamentals``

**Step 4: Verify clause references** against the clause structure skills
(``iso-26262-structure``, etc.) before presenting to an assessor. Every clause
reference in a qualification artifact should be verifiable against the
published standard.

Example: Authoring Software Requirements for an ASIL D C Library
=================================================================

**Agent loads (in order):**

1. ``functional-safety-index`` — navigation hub, confirms software task routing
2. ``iso-26262-application`` — loads Part 6 clause requirements (R-036 through R-042),
   Part 10 SEooC guidance (R-054), Part 8 tool qualification (R-053)
3. ``iso26262-part6-software`` — gets OSQAr need ID conventions (REQ_SSR_*),
   ASIL-differentiated requirement rigour table, RST examples
4. ``osqar-qualification`` — gets CLI commands for scaffolding, building,
   traceability checks, shipment packaging (the *how* of using OSQAr)

**Agent then authors:**

* ``01_requirements.rst`` — REQ_SSR_NOMINAL_*, REQ_SSR_FAULT_*, etc.
  following the Part 6 Table 7 techniques table and ASIL D rigour
* ``02_architecture.rst`` — ARCH_* needs with static/dynamic views,
  freedom from interference, safety mechanism patterns
* ``03_verification.rst`` — VER_* needs with MC/DC coverage targets,
  static analysis, fault injection, tool qualification
* ``06_lifecycle_management.rst`` — 5 AoUs for the SEooC per Part 10 §9.4.2

**Agent finally runs:**

.. code-block:: bash

   osqar new --language c --name my-lib-qualification --template asil-d-c
   # ... author documents ...
   python3 -m sphinx -b html -W . _build/html
   osqar traceability _build/html/needs.json --test-prefix VER_ --code-prefix IMPL_
   osqar shipment prepare --project .

Clause Verification Gateway
===========================

Every claim about a standard requirement must be verifiable. Before making a
claim in a qualification artifact:

1. **Check the content-authoring skill** — does it reference the clause?
2. **Check the research skill** — does the clause-level requirement exist?
   (Example: ``iso-26262-application`` lists R-036 through R-042 for Part 6)
3. **Verify the clause exists** — use ``search_files`` on the structure skills
   to confirm the clause number and title (e.g., search for ``6.4.1`` in
   ``iso-26262-structure``)
4. **If unverifiable** — mark as "informed opinion" not "normative requirement"
   and do NOT cite a clause reference

Evidence Quality Gate
=====================

When agents generate qualification evidence (verification results, coverage reports):

1. **All evidence MUST come from live tool runs** — never hand-written numbers
2. **Every tool invocation MUST record**: tool name + version, configuration,
   input data, output, date, operator
3. **Coverage reports MUST name the specific tool**: "gcov/lcov v1.16" not "coverage tool"
4. **Agent-generated content MUST be reviewed by a human engineer** before
   inclusion in the qualification baseline
5. **Traceability MUST be bidirectional**: every requirement-to-verification link is verifiable

Common Pitfalls for Agents
===========================

1. **Inventing clause numbers** — always verify against structure skills before
   citing a clause reference. Agents hallucinate plausible-sounding clause
   numbers that don't exist in the standard.
2. **Overclaiming compliance** — never use "ASIL D compliant" or "ISO 26262 certified."
   Always use "qualification attempt targeting ASIL D" or "developed per
   ISO 26262:2018 processes."
3. **Confusing tools with techniques** — "unit testing" is a technique; "CUnit 3.2.7"
   is a tool. The standard requires both: the technique must be applied (Part 6
   Table 9) and the tool must be qualified (Part 8 §11).
4. **Forgetting the safety manual** — for SEooC qualification, the safety manual
   (including AoUs) is as important as the safety case. The integrator cannot
   use the component safely without it.
5. **Presenting traceability as compliance** — a complete traceability matrix
   proves links exist but does not prove requirements are correct, verification
   is adequate, or evidence is valid.
6. **Missing Part 8 supporting processes** — tool qualification (R-053),
   configuration management (R-049), change management (R-050), and
   documentation management (R-052) apply to ALL parts and are frequently
   overlooked in single-component SEooC qualifications.
7. **Assuming verification tools don't need qualification** — every tool in
   the safety toolchain must be classified (TI/TD → TCL). Even CI/CD tools
   that transform source code are in scope per Part 8 §11.
8. **Not consulting the ``osqar-qualification`` skill** — the tool-usage skill
   documents the exact CLI commands, project structure, and pitfalls for the
   OSQAr framework itself. It is complementary to the content-authoring skills
   and should always be loaded when using OSQAr.

Further Reading
===============

* ``skills/SKILL_INDEX.md`` — complete skill catalogue with recommended reading orders
* ``skills/README.md`` — disclaimer and LLM usage guidance
* ``skills/iso26262-part6-software/SKILL.md`` — software content-authoring reference
* :doc:`suppliers_guide` — producing auditable evidence shipments
* :doc:`integrators_guide` — receiving and verifying supplier evidence
* :doc:`lifecycle_management` — configuration baselines, AoUs, tool qualification
* :doc:`cli_reference` — all OSQAr commands with synopsis and examples
