---
name: iso26262-part6-software
description: Author ISO 26262-6 software requirements, architecture, and verification content for OSQAr qualification projects. ASIL-differentiated guidance with clause references.
version: 1.0.0
license: Apache-2.0
---

# ISO 26262 Part 6 — Software Development for OSQAr Qualification

## Overview

This skill maps ISO 26262-6:2018 (Product development at the software level) onto OSQAr
qualification artifacts. Use it when authoring `01_requirements.rst`, `02_architecture.rst`,
`03_verification.rst`, `04_implementation.rst`, and `06_lifecycle_management.rst` for
automotive software SEooC qualification.

The guidance is ASIL-differentiated: requirements increase in rigour from ASIL A to ASIL D
per ISO 26262-6:2018 Tables 3-11.

## When to Use

- Scaffolding a new OSQAr qualification project for automotive software
- Authoring software safety requirements (SSRs) from Technical Safety Requirements (TSRs)
- Designing software architecture with safety mechanisms
- Planning verification strategies with coverage targets
- Documenting Assumptions of Use for a software SEooC

## Software Safety Requirements → `01_requirements.rst`

### Input Sources

SSRs are derived from:
- Technical Safety Requirements (TSRs) allocated to software — ISO 26262-4 §6.4.6
- Hardware-Software Interface (HSI) specification — ISO 26262-4 §6.4.7
- System architectural design constraints — ISO 26262-4 §6.4.3
- Assumptions of Use for SEooC — general guidance in ISO 26262-10 §9.1

### OSQAr Need ID Conventions

```
REQ_SSR_<CATEGORY>_<NNN>
```

Categories: `NOMINAL`, `FAULT`, `INIT`, `SHUTDOWN`, `INTERFACE`, `TIMING`,
`MONITOR`, `MEMORY`, `REDUNDANCY`, `DIAG`, `CONFIG`, `EXTASSUME`.

### ASIL-Differentiated Requirement Rigour

| Aspect | ASIL A | ASIL B | ASIL C | ASIL D |
|--------|--------|--------|--------|--------|
| Specification formality | Natural language | Structured natural language | Semi-formal notation | Semi-formal + formal elements |
| Requirement attributes | ID, text, ASIL | + status, trace | + verification method | + acceptance criteria, rationale |
| Review independence | Author review | I1 (different person) | I2 (different team) | I2+ (different department) |
| Traceability | Forward only | Bidirectional | Bidirectional + impact analysis | Bidirectional + CI-automated |

This rigour matrix is OSQAr project policy; it is not derived from
ISO 26262-6:2018 Table 1; that table addresses topics covered by modelling and
coding guidelines.

### Requirement Classes (all ASILs)

For each safety-relevant software function, define REQ_ needs covering:

| Requirement Class | `01_requirements.rst` Section | Mandatory At |
|---|---|---|
| Nominal functional behavior | Nominal Operation | All ASILs |
| Fault detection behaviour | Fault Detection | All ASILs |
| Fault reaction / degradation | Fault Reaction | All ASILs |
| Initialization and startup | Initialization | All ASILs |
| Shutdown and restart | Shutdown | ASIL B+ |
| Interface validation | Interface Validation | ASIL B+ |
| Timing constraints | Timing | ASIL B+ |
| Data freshness / sequencing | Data Integrity | ASIL B+ |
| Monitoring and supervision | Monitoring | ASIL B+ |
| Memory integrity | Memory Safety | ASIL C+ |
| Redundancy / cross-check | Redundancy | ASIL C+ |
| Diagnostic reporting | Diagnostics | ASIL B+ |
| Configuration restrictions | Configuration | All ASILs |
| External assumptions | Assumptions of Use | All ASILs (SEooC) |
| Verification criteria | Acceptance Criteria | All ASILs |

Reference: ISO 26262-6 §6.4.1.

### Example OSQAr RST

```rst
.. need:: The monitoring task shall detect implausible torque within 10 ms
          of command and assert the disable signal.
   :id: REQ_SSR_FAULT_001
   :status: active
   :tags: ASIL_D;fault_detection;torque_monitoring
   :links: ARCH_MON_TASK;VER_FAULT_INJECT_001

   **Source TSR:** TSR_TORQUE_MON_001 (ISO 26262-4 §6.4.1)
   **Detection interval:** ≤10 ms
   **Reaction:** Assert DISABLE signal within 5 ms of detection
   **Verification:** Fault injection — corrupt torque command, measure reaction time
```

## Software Architecture → `02_architecture.rst`

### Architecture Views

ISO 26262-6 §7.4.5 provides the architectural-view context. OSQAr documents
the following project-selected views as `ARCH_` needs:

| View | Description | OSQAr Section |
|------|-------------|---------------|
| Static decomposition | Components, interfaces, ASIL allocation | Static Structure |
| Dynamic behaviour | Task scheduling, inter-task communication | Dynamic Behaviour |
| Data flow | Data dependencies, ownership, freshness | Data Flow |
| Control flow | Mode transitions, state machines | Control Flow |
| Fault handling | Detection and reaction paths | Fault Handling |
| Startup/shutdown | Init sequence, shutdown sequence, reset | Startup/Shutdown |
| External dependencies | Platform, OS, watchdog, BSW interfaces | External Dependencies |

### ASIL-Differentiated Design Principles

ISO 26262-6:2018 Table 3 identifies principles for software architectural
design and gives ASIL-dependent recommendation strengths. Use the packaged
catalog for its controlled locator and topic. Select, tailor, and justify the
applicable principles for the project; do not treat this skill as a
reproduction of the table or as a universal fixed method set.

### Freedom from Interference

When elements of different ASIL coexist (mixed-criticality), document per ISO 26262-9 §6:

- **Spatial**: Memory partitioning (MPU/MMU) between ASIL levels
- **Temporal**: Scheduling guarantees — higher-ASIL tasks meet deadlines regardless
- **Communication**: E2E protection, data validation across partitions

```rst
.. arch:: The torque monitoring task (ASIL D) executes in a dedicated MPU
         region with write-protected code and exclusive data section.
   :id: ARCH_FFI_SPATIAL
   :tags: ASIL_D;freedom_from_interference;MPU
   :links: REQ_SSR_FAULT_001;VER_FFI_ANALYSIS
```

### Safety Mechanism Patterns

The following is an OSQAr project pattern, not a paraphrase of
ISO 26262-6:2018 Tables 4/5. Table 4 addresses software-architecture
verification methods; Table 5 addresses notation methods for software unit
design, not error detection or error handling:

```rst
.. arch:: Plausibility check: commanded torque vs. measured torque.
         Difference > 10% for > 2 consecutive samples → fault.
   :id: ARCH_MON_PLAUSIBILITY
   :tags: ASIL_D;plausibility_check;safety_mechanism
   :links: REQ_SSR_FAULT_001
```

## Software Verification → `03_verification.rst`

### Coverage and Verification Reference Map

Use the packaged catalog rather than reproducing recommendation ratings here.
The researched mappings are:

- ISO 26262-6:2018 Tables 7/8 — software-unit verification and unit-test derivation;
- ISO 26262-6:2018 Table 9 — software-unit structural coverage;
- ISO 26262-6:2018 Tables 10/11 — software-integration verification and test derivation;
- ISO 26262-6:2018 Table 12 — software-architecture structural coverage; and
- ISO 26262-6:2018 Table 13 — test environments for embedded-software testing;
- ISO 26262-6:2018 Table 14 — embedded-software test methods; and
- ISO 26262-6:2018 Table 15 — embedded-software test-case derivation methods.

Exact percentages and acceptance thresholds in examples are OSQAr project
policy. The table subjects above were checked against the controlled 2018 copy;
their applicability and project use still require competent review.

### OSQAr VER_ Needs — Example

```rst
.. ver:: Unit test coverage: all torque monitoring functions achieve
        statement coverage ≥ 100%, branch coverage ≥ 100%,
        MC/DC coverage ≥ 100% (ASIL D target).
   :id: VER_COVERAGE_TORQUE
   :tags: ASIL_D;coverage;MC/DC;unit_test
   :links: REQ_SSR_FAULT_001;ARCH_MON_TASK

   **Tool:** gcov/lcov v1.16
   **Configuration:** --branch-probabilities, --all-blocks
   **Target:** Statement 100%, Branch 100%, MC/DC 100%
   **Result:** Statement 100% (234/234), Branch 100% (156/156),
              MC/DC 98.7% (152/154) — uncovered pair justified
              (dead code after defensive range check)
```

### Tool Qualification

ISO 26262-8:2018 Clause 11 is the researched tool-confidence reference. Tool
classification and any qualification conclusion require a project-specific
assessment; do not copy fixed TI/TD/TCL results.

```rst
.. lm:: Tool Confidence Level determination for verification toolchain.
   :id: LM_TOOL_TCL
   :tags: tool_qualification;TCL

   **Compiler:** <project analysis and reviewed result>
   **Static analyzer:** <project analysis and reviewed result>
   **Test framework:** <project analysis and reviewed result>
   **Coverage tool:** <project analysis and reviewed result>
```

## Implementation → `04_implementation.rst`

The following are conservative OSQAr project-policy defaults. Do not attribute
them to Tables 7/8; the researched catalog maps those tables to software-unit
verification and test derivation.

### Mandatory Implementation Rules by ASIL

| Rule | ASIL A | ASIL B | ASIL C | ASIL D |
|------|--------|--------|--------|--------|
| One entry, one exit | ++ | ++ | ++ | ++ |
| No dynamic objects after init | — | + | ++ | ++ |
| No recursion | — | — | ++ | ++ |
| Limited pointer use | — | + | + | ++ |
| Defensive implementation | — | + | + | ++ |
| Coding standard enforced | + | ++ | ++ | ++ |
| Automated static analysis | + | ++ | ++ | ++ |

Example coding standards: MISRA C:2012, AUTOSAR C++14, CERT C.

### OSQAr IMPL_ Needs — Example

```rst
.. impl:: Source inventory with ASIL classification and coding standard
         compliance status.
   :id: IMPL_INVENTORY
   :tags: ASIL_D;source_inventory;MISRA_C

   **Total modules:** 14 (8 ASIL D, 4 ASIL B, 2 QM)
   **Coding standard:** MISRA C:2012 Directive 4.14 (Mandatory)
   **Static analysis:** cppcheck 2.14 with MISRA addon
   **Build reproducibility:** Verified against OSQAr project policy
```

## Lifecycle Management → `06_lifecycle_management.rst`

### Assumptions of Use for Software SEooC

ISO 26262-10:2018 Clause 9 provides researched informative SEooC guidance. Document the
project's actual assumptions; OSQAr does not prescribe a standards-derived
minimum count. This is a project-authored mapping.

```rst
.. lm:: Integration context: the software assumes single-core execution
       with priority-based preemptive scheduling.
   :id: LM_AOU_INTEGRATION
   :tags: SEooC;assumption_of_use;integration

.. lm:: Input constraints: all sensor inputs are pre-validated for range
       and freshness by hardware diagnostics before software processing.
   :id: LM_AOU_INPUTS
   :tags: SEooC;assumption_of_use;input_validation
   :links: ARCH_EXT_DIAG;REQ_SSR_EXTASSUME_001
```

### Configuration Management Baseline

Per ISO 26262-8 §7:

```rst
.. lm:: Configuration baseline at software release.
       All safety artifacts under version control.
   :id: LM_CM_BASELINE
   :tags: configuration_management;baseline

   **Repository:** <repo-url>
   **Tag:** v1.7.19-0.9.0
   **Artifacts:** 01-06 RST, conf.py, osqar_project.json, source code
```

## Cross-References

- **ISO 26262-6** — all clause references in this skill
- **ISO 26262-4 §6.4.1-§6.4.6** — TSR allocation to software
- **ISO 26262-4 §6.4.7** — HSI specification
- **ISO 26262-8 §7, §8, §11** — supporting processes
- **ISO 26262-9 §5, §6** — ASIL decomposition, coexistence
- **ISO 26262-10 §9** — SEooC framework

## Pitfalls

1. **Copying Part 6 tables into requirements without context** — the tables give
   method recommendations within normative clauses; they do not turn an untailored
   OSQAr example into a project requirement. Requirements must be project-specific.
2. **Claiming ASIL D compliance** — always use "qualification attempt targeting
   ASIL D" language. Formal compliance requires independent assessment.
3. **Missing HSI in SSRs** — software requirements that don't reference
   hardware-software interfaces create untestable assumptions.
4. **Coverage ≠ correctness** — 100% MC/DC coverage means code was exercised,
   not that it's correct. Tests must be requirements-based.
5. **Presenting coding policy as controlled text** — restrictions on dynamic
   allocation and recursion are OSQAr scaffold policy until a project cites
   reviewed controlled text precisely; Table 7 is not their catalog mapping.
