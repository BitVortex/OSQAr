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
per Part 6 Tables 3-11.

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
- Hardware-Software Interface (HSI) specification — ISO 26262-4 §7.4
- System architectural design constraints — ISO 26262-4 §6.4.3
- Assumptions of Use for SEooC — ISO 26262-10 §9.4.2

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

Reference: ISO 26262-6 §6.4.2, Table 1.

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

Per ISO 26262-6 §7.4.3, document these views as `ARCH_` needs:

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

Per ISO 26262-6 Table 3:

| Principle | ASIL A | ASIL B | ASIL C | ASIL D |
|-----------|--------|--------|--------|--------|
| Hierarchical structure | + | ++ | ++ | ++ |
| Restricted size/complexity | — | + | + | ++ |
| Strong cohesion | + | + | ++ | ++ |
| Loose coupling | + | + | ++ | ++ |
| Appropriate scheduling | + | ++ | ++ | ++ |
| Restricted interrupts | — | — | + | ++ |

++ = highly recommended, + = recommended, — = no recommendation

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

Per ISO 26262-6 Table 4 (error detection) and Table 5 (error handling):

```rst
.. arch:: Plausibility check: commanded torque vs. measured torque.
         Difference > 10% for > 2 consecutive samples → fault.
   :id: ARCH_MON_PLAUSIBILITY
   :tags: ASIL_D;plausibility_check;safety_mechanism
   :links: REQ_SSR_FAULT_001
```

## Software Verification → `03_verification.rst`

### Coverage Targets by ASIL

Per ISO 26262-6 Table 10 (unit level) and Table 11 (architectural level):

| Coverage Metric | ASIL A | ASIL B | ASIL C | ASIL D |
|-----------------|--------|--------|--------|--------|
| Statement (unit) | ++ | ++ | ++ | + |
| Branch (unit) | + | ++ | ++ | ++ |
| MC/DC (unit) | — | + | + | ++ |
| Function (arch.) | + | + | ++ | ++ |
| Call (arch.) | + | + | ++ | ++ |

++ = highly recommended, + = recommended, — = no recommendation

### Verification Methods by ASIL

Per ISO 26262-6 Table 9:

| Method | ASIL A | ASIL B | ASIL C | ASIL D |
|--------|--------|--------|--------|--------|
| Walk-through | ++ | + | — | — |
| Inspection | + | ++ | ++ | ++ |
| Static analysis | + | ++ | ++ | ++ |
| Unit testing | ++ | ++ | ++ | ++ |
| Integration testing | + | ++ | ++ | ++ |
| Formal verification | — | — | + | + |

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

Verification tools must be classified per ISO 26262-8 §11.4:

```rst
.. lm:: Tool Confidence Level determination for verification toolchain.
   :id: LM_TOOL_TCL
   :tags: tool_qualification;TCL

   **Compiler:** TI2, TD3 → TCL3 — qualification required
   **Static analyzer:** TI2, TD2 → TCL2 — increased confidence from use
   **Test framework:** TI1 → TCL1 — no qualification needed
   **Coverage tool:** TI1, TD1 → TCL1 — no qualification needed
```

## Implementation → `04_implementation.rst`

Per ISO 26262-6 Table 7 (modeling/coding guidelines) and Table 8 (design principles):

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
   **Build reproducibility:** Verified per ISO 26262-8 §11.4.8
```

## Lifecycle Management → `06_lifecycle_management.rst`

### Assumptions of Use for Software SEooC

Per ISO 26262-10 §9.4.2, document at minimum:

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
- **ISO 26262-4 §7.4** — HSI specification
- **ISO 26262-8 §7, §8, §11** — supporting processes
- **ISO 26262-9 §5, §6** — ASIL decomposition, coexistence
- **ISO 26262-10 §9** — SEooC framework

## Pitfalls

1. **Copying Part 6 tables into requirements without context** — the tables are
   informative guidance, not requirements. Requirements must be project-specific.
2. **Claiming ASIL D compliance** — always use "qualification attempt targeting
   ASIL D" language. Formal compliance requires independent assessment.
3. **Missing HSI in SSRs** — software requirements that don't reference
   hardware-software interfaces create untestable assumptions.
4. **Coverage ≠ correctness** — 100% MC/DC coverage means code was exercised,
   not that it's correct. Tests must be requirements-based.
5. **Dynamic memory in ASIL C/D** — ISO 26262-6 Table 7 strongly discourages
   dynamic allocation at ASIL B+ and effectively prohibits at ASIL C/D.
