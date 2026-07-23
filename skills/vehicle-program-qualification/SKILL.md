---
name: vehicle-program-qualification
description: Scale OSQAr qualification from single-component SEooC to multi-ECU vehicle programs. Covers distributed development, DIA management, cross-ECU safety case composition, and supplier evidence aggregation.
version: 1.0.0
license: Apache-2.0
---

# Industry-Scale Automotive Qualification with OSQAr

## Overview

This skill covers scaling OSQAr from a single-component SEooC qualification
to a multi-ECU, multi-supplier, full-vehicle ISO 26262 program. A single
component's qualification is fundamentally simpler than a vehicle program
with 50-100+ ECUs from 20+ suppliers.

Use this skill when the qualification scope extends beyond a single software
component to include system-level integration, distributed development, and
cross-ECU safety case composition.

## When to Use

- Qualifying a vehicle-level function that spans multiple ECUs
- Integrating supplier SEooC evidence into a system-level safety case
- Managing Development Interface Agreements (DIAs) across organizations
- Composing safety cases from independently-qualified components
- Handling mixed-criticality systems (ASIL D + ASIL B + QM on one ECU)

## Scale Challenges

| Aspect | Single SEooC | Vehicle Program |
|--------|-------------|-----------------|
| Components | 1 software library | 50-100+ ECUs |
| Suppliers | 1 (self-contained) | 20+ organizations |
| Safety goals | 3-5 (component-level) | 50-200+ (vehicle-level) |
| Integration levels | HW/SW only | Component → ECU → subsystem → vehicle |
| Safety case | Single argument | Hierarchical, multi-layered |
| Change management | Simple (single repo) | Cross-organizational impact analysis |
| Production | Not applicable | Process FMEA, end-of-line testing |
| Field monitoring | Not applicable | Fleet-wide data collection, statistical analysis |

## OSQAr Workspace Patterns

### Pattern 1: Per-ECU Qualification Repos

Each ECU has its own OSQAr qualification repo with its own needs,
traceability, and shipment:

```
fleet/
├── braking_ecu/          (supplier A, ASIL D)
│   ├── 01_requirements.rst
│   ├── 02_architecture.rst
│   ├── ...
│   └── _build/html/needs.json
├── steering_ecu/         (supplier B, ASIL D)
│   ├── ...
│   └── _build/html/needs.json
├── adas_controller/      (supplier C, ASIL B + QM)
│   ├── ...
│   └── _build/html/needs.json
└── vehicle_integration/  (OEM, system-level)
    ├── 01_requirements.rst  ← vehicle-level safety goals
    ├── 02_architecture.rst  ← ECU network topology
    └── workspace.needs.json ← combined via osqar workspace combine
```

### Pattern 2: Workspace Combine

`osqar workspace combine` merges multiple project `needs.json` exports
with namespace prefixes for cross-project traceability (OSQAr v0.7.3+):

```bash
# Combine all ECU-level needs into a vehicle-level workspace
osqar workspace combine --root fleet/

# Run cross-ECU traceability
osqar workspace traceability     --needs-json fleet/_build/workspace/needs.json     --req-prefix braking_ecu:REQ_ steering_ecu:REQ_ adas_controller:REQ_
```

Each project's needs get a `<project-name>:` prefix. Links are rewritten
with prefixed IDs, enabling end-to-end traceability from vehicle-level
safety goals to supplier-level verification evidence.

### Pattern 3: Vehicle-Level Safety Case Composition

The vehicle-level safety case is hierarchical, composed from per-ECU
safety cases with integration arguments:

```rst
.. sc:: Vehicle-level claim: the braking system achieves
       ASIL D safety integrity with no single-point failures
       that could cause unintended loss of braking.
   :id: SC_VEHICLE_BRAKING_TOP
   :tags: ASIL_D;vehicle_level;braking

   **Composed from:**
   - braking_ecu:SC_TOP (supplier A — brake controller SEooC)
   - steering_ecu:SC_TOP (supplier B — required for brake-steer coordination)
   - vehicle_integration:SC_INTEGRATION (OEM — integration validation)
```

## Development Interface Agreement (DIA) Management

For distributed development to which ISO 26262-8 Clause 5 applies, establish a
Development Interface Agreement covering the applicable division of activities
and responsibilities. Do not infer that every commercial supplier relationship
is necessarily within that scope. OSQAr records:

| DIA Element | OSQAr Documentation |
|-------------|---------------------|
| Safety responsibilities | `LM_DIA_RESPONSIBILITY` — per-supplier RACI |
| Safety lifecycle activities | `LM_DIA_LIFECYCLE` — which phases each party executes |
| Work products exchanged | `LM_DIA_WORKPRODUCTS` — needs.json, shipment, evidence |
| Communication paths | `LM_DIA_COMMUNICATION` — escalation, reporting |
| Safety managers | `LM_DIA_MANAGERS` — named roles per party |

```rst
.. lm:: DIA with Supplier A (brake controller): Supplier A is
       responsible for software development per ISO 26262-6
       targeting ASIL D. OEM is responsible for system integration
       per ISO 26262-4 and vehicle validation per ISO 26262-4 §8.
   :id: LM_DIA_BRAKING
   :tags: DIA;supplier_management;ISO_26262-8_§5
   :links: braking_ecu:LM_SCOPE;vehicle_integration:LM_INTEGRATION

   **Supplier scope:** Software SEooC — ISO 26262-6, ISO 26262-8:2018 §11 (tools),
   ISO 26262-9:2018 §5 (decomposition if applicable)
   **OEM scope:** System integration ISO 26262-4 §7;
   vehicle validation ISO 26262-4 §8;
   production ISO 26262-7
   **Exchange format:** OSQAr shipment packages (needs.json + evidence)
   **Escalation:** Safety manager → project safety manager → executive
                    steering committee within 48h for critical findings
```

## Cross-ECU Safety Mechanisms

Many vehicle-level safety mechanisms span ECUs and require coordinated
qualification:

| Mechanism | ECUs Involved | OSQAr Traceability |
|-----------|---------------|---------------------|
| E2E protection | Sender ECU + Receiver ECU | `ARCH_E2E_PROTECTION` linked across repos |
| Watchdog / alive supervision | Application ECU + System Basis Chip | `ARCH_WATCHDOG` with external assumption |
| Torque monitoring (E-Gas) | Engine ECU + Monitoring ECU | `ARCH_EGAS_LEVEL2` + `ARCH_EGAS_LEVEL3` |
| Degradation coordination | Multiple ECUs (fail-operational) | `ARCH_DEGRADATION` with state machine across ECUs |

```rst
.. arch:: E2E protection: all CAN-FD messages between brake ECU
         (sender) and chassis domain controller (receiver) use
         AUTOSAR E2E Profile 1 with CRC-8 and 4-bit sequence counter.
   :id: ARCH_E2E_BRAKE_CHASSIS
   :tags: ASIL_D;E2E_protection;CAN_FD
   :links: REQ_COMM_INTEGRITY;braking_ecu:ARCH_CAN_TX;
           chassis_ctrl:ARCH_CAN_RX;VER_E2E_FAULT_INJECT
```

## Mixed-Criticality Systems

When ASIL D, ASIL B, and QM components share an ECU, document
freedom from interference per ISO 26262-9 §6:

```rst
.. arch:: Freedom from interference: the ASIL D torque monitoring
         task runs in a dedicated MPU partition (region 0x20010000,
         64 KB, read-execute for code, read-write for data).
         ASIL B communication stack tasks run in separate partitions
         with time-triggered scheduling (TDMA, 5 ms slots).
         QM infotainment bridge runs in the lowest-priority partition
         with MPU-protected shared memory access.
   :id: ARCH_FFI_BRAKE_ECU
   :tags: ASIL_D;freedom_from_interference;MPU;TDMA
   :links: VER_FFI_ANALYSIS;VER_FFI_FAULT_INJECT
```

## Supplier Evidence Aggregation

When integrating evidence from multiple suppliers, establish a consistent
evidence format and quality bar:

```rst
.. lm:: Supplier evidence quality gate: all supplier OSQAr shipments
       must include:
       1. Signed SHA256SUMS manifest (OSQAr v0.7.3+ GPG signing)
       2. needs.json with bidirectional traceability
       3. Verification evidence from live tool runs (not hand-written)
       4. Project Assumptions of Use catalogue (general SEooC guidance:
          ISO 26262-10 §9.1)
       5. Project-specific tool-confidence analysis and any resulting
          qualification evidence under ISO 26262-8 Clause 11
       6. Supplier safety case contribution

       Minimum acceptance criteria:
       - Zero traceability violations (osqar traceability check passes)
       - All REQ_ needs at target ASIL have at least one VER_ link
       - Coverage reports generated by automated tool (not hand-entered)
       - Shipment hash verified (osqar checksum verify passes)
   :id: LM_SUPPLIER_GATE
   :tags: supplier_management;evidence_quality;shipment
```

## Change Management at Scale

A vehicle program spans 3-5 years with hundreds of changes. ISO 26262-8
§§8.4.3–8.4.4 provide the impact-analysis basis for applicable changes. This
OSQAr project workflow records:

1. **Change impact analysis** — which ECUs, safety goals, and verification
   evidence are affected?
2. **Cross-supplier notification** — change in ECU A may invalidate
   ECU B's assumptions
3. **Regression verification scoping** — re-verify only what has changed
   or been impacted
4. **Safety case update** — if the safety argument changes, the safety
   case must be updated

OSQAr's `osqar baseline` and `osqar impact` commands support this:

```bash
# Before change: snapshot current baseline
osqar baseline snapshot --tag pre_change_v2.3

# After change: diff to see what changed
osqar baseline diff pre_change_v2.3 post_change_v2.4

# Impact analysis: transitive closure from changed need
osqar impact _build/html/needs.json --need-id REQ_SSR_FAULT_001     --direction downstream --max-depth 5 --json-report impact_analysis.json
```

## Production and Field Monitoring

For production-intent vehicle programs, the following are project implementation
examples informed by ISO 26262-7, not universal prescriptions:

```rst
.. lm:: Production safety: this project uses an end-of-line test for all ECUs
       to verify its selected safety-related functions. ISO 26262-7 §6.4
       provides production-planning and control context.
       Test results archived with VIN traceability.
   :id: LM_PRODUCTION_EOL
   :tags: production;safety;ISO_26262-7

.. lm:: Field monitoring: this project uses fleet-wide data collection for
       safety-related anomalies and project-defined investigation triggers.
       ISO 26262-7 §7.4 provides operation, service, maintenance, and
       decommissioning context.
   :id: LM_FIELD_MONITORING
   :tags: field_monitoring;ISO_26262-7;post_production

   **Data sources:** Warranty claims, service records, telematics,
      incident reports, recall database
   **Analysis:** Statistical comparison of observed vs. predicted
      failure rates (FMEDA baseline)
   **Project trigger criteria:** Observed rate > 2× predicted rate OR
      any single incident with potential for catastrophic harm
   **Response time:** Investigation initiated within 5 business days
```

## Cross-Standard Integration

At industry scale, multiple standards apply simultaneously:

| Standard | Scope | OSQAr Integration |
|----------|-------|-------------------|
| ISO 26262 | Functional safety | Primary qualification workflow |
| ISO 21434 | Cybersecurity | `security-coengineering` skill |
| ISO 21448 | SOTIF (ADAS) | `sotif-qualification` skill |
| ISO 26262-11 §4.7.8 | Semiconductors | Dependent software/hardware failures |
| ISO 26262-11 §4.8 | Semiconductors | Fault-injection guidance |
| ISO 26262-8 §11 | Confidence in software-tool use | Use-case analysis and reviewed result in LM_ needs |
| UN R155/R156 | Cybersecurity/SW update regulation | Evidence from cybersecurity workflow |

For co-engineering across standards, use the `:collapsed:` field to link
related needs across domains, and the workspace combine feature to aggregate
evidence at the vehicle level.

## Pitfalls

1. **Assuming suppliers have done their job** — integrator must validate
   supplier assumptions of use against actual integration context.
   A supplier's SEooC qualification is only valid when AoUs are met.
2. **Forgetting integration validation** — testing each ECU independently
   does not validate the system-of-systems. Integration faults (timing,
   E2E, shared resource contention) are the most common vehicle-level
   safety issues.
3. **Late safety case** — the safety case must evolve with the project.
   A safety case written just before SOP is unlikely to survive
   independent assessment.
4. **Toolchain divergence** — suppliers using different compiler versions
   or static analysis configurations create evidence incompatibility.
   Standardize tool versions in the DIA.
5. **Proven-in-use complacency** — "we've shipped 10 million units"
   is not a safety argument without documented field data analysis
   per ISO 26262-8 §14.
6. **Uncontrolled supplier changes** — a supplier changing their
   implementation without notifying the integrator can invalidate
   the integration safety case. DIA must require change notification.
