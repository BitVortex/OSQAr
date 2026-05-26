---
name: sotif-qualification
description: Add ISO 21448 SOTIF qualification content to OSQAr projects. Map triggering events, sensor/algorithm limitations, scenario-based validation, and residual risk to OSQAr REQ/VER/SC needs.
version: 1.0.0
license: MIT
---

# SOTIF Qualification with OSQAr

## Overview

This skill maps ISO 21448:2022 — Safety of the Intended Functionality (SOTIF)
onto OSQAr qualification artifacts. It addresses hazards caused by functional
insufficiencies (performance limitations of sensors, algorithms, and actuators)
rather than by system malfunctions (which are covered by ISO 26262).

SOTIF is critical for ADAS and automated driving systems (SAE Levels 1-5)
where the system may be working exactly as designed, yet the design itself
is insufficient for safety.

**Standard evolution:** ISO/PAS 21448:2019 (first edition, PAS) was published
in January 2019 with 66 pages, 12 clauses, and 7 informative annexes.
It was later revised to ISO 21448:2022 as a full International Standard
with expanded scope and clarified requirements.

## When to Use

- Qualifying ADAS/autonomous driving components (perception, planning, control)
- Addressing sensor limitations (camera, lidar, radar, ultrasonic)
- Handling ML-based perception systems where performance is statistical, not deterministic
- Defining scenario-based validation campaigns
- Evaluating residual risk after all functional modifications are applied
- Documenting reasonably foreseeable misuse scenarios

## Core Concepts

### ISO 26262 vs. ISO 21448

```
ISO 26262: System fails (malfunction) → hazard
ISO 21448: System works as designed, but design is insufficient → hazard

Examples:
- 26262: Radar firmware crashes → no obstacle detection → collision
- 21448: Radar cannot detect stopped vehicle at >100m range → collision
         despite working correctly

Both must be addressed. They are complementary, not alternatives.
```

### SOTIF Zone Model

The standard defines four zones based on known/unknown combinations:

```
                      | Hazardous behaviour known | Hazardous behaviour unknown
----------------------|--------------------------|---------------------------
Scenario known        | Area 2 (Verified)        | Area 3 (Validated)
Scenario unknown      | Area 3 (Validated)       | Area 3 (unknown → known)
```

- **Area 1**: Known safe scenarios — no SOTIF risk
- **Area 2**: Known hazardous scenarios with known causes — addressed by
  verification (ISO 21448 §10)
- **Area 3**: Unknown hazardous scenarios or unknown causes — addressed by
  validation (ISO 21448 §11)
- **Goal**: Minimize Areas 2 and 3 to an acceptable residual risk level

### Triggering Events

Specific operating conditions that cause a functional insufficiency to
become hazardous (ISO 21448 §7.2):

| Category | Examples | Analysis Method |
|----------|----------|-----------------|
| Algorithm limitations (§7.2.1) | ML misclassification of rare objects; planning edge case | Scenario catalog + simulation |
| Sensor limitations (§7.2.2) | Camera blinded by low sun; lidar attenuated by fog | Environmental chamber + field testing |
| Actuator limitations (§7.2.2) | Steering rate limit in emergency manoeuvre | Dynamics simulation + vehicle test |
| Environmental conditions | Unusual road geometry; degraded lane markings | Map-based scenario injection |
| Reasonably foreseeable misuse | Driver overreliance on L2 system | User study + misuse scenario derivation (Annex E) |

## Document Structure

### 01_requirements.rst — SOTIF Requirements

Add `REQ_SOTIF_*` needs derived from the functional specification and
triggering event analysis:

```rst
.. need:: The perception system shall detect stationary vehicles
          at ≥150 m range under clear weather conditions,
          ≥100 m under light fog, and ≥80 m under heavy rain.
   :id: REQ_SOTIF_PERCEP_001
   :status: active
   :tags: SOTIF;sensor_limitation;radar;range
   :links: VER_SOTIF_RANGE_TEST;SC_SOTIF_PROPERTY

   **Triggering event source:** TE-007 — radar range degradation
   in adverse weather (ISO 21448 §7.2.2)
   **Validation target:** False negative rate < 10⁻⁶ per km
   **Acceptance criteria:** Validated per scenario catalog SCEN-*
```

```rst
.. need:: The lane-keeping algorithm shall maintain lane position
          within ±30 cm under all road curvature > 200 m radius
          with clearly marked lane lines (dashed or solid, white or yellow).
   :id: REQ_SOTIF_ALGO_001
   :tags: SOTIF;algorithm_limitation;lane_keeping;curvature
   :links: VER_SOTIF_CURVE_TEST

   **Limitation acknowledged:** Performance degrades at curvature
   < 200 m radius — documented as functional insufficiency,
   driver expected to take over (HMI warning at 250 m radius).
```

### System Specification (§5)

```rst
.. need:: Functional description: the automated emergency braking
          (AEB) function detects obstacles in the vehicle path and
          applies braking to avoid or mitigate collision.
   :id: REQ_SOTIF_FUNCSPEC
   :tags: SOTIF;functional_spec;AEB

   **Operational Design Domain (ODD):**
   - Speed: 5-80 km/h (city), 60-130 km/h (highway)
   - Road type: Paved roads with lane markings
   - Weather: Clear to light rain (no heavy precipitation)
   - Lighting: Daylight + night (headlights required)
   - Object types: Vehicles, pedestrians, cyclists, motorcycles

   **Out of scope (limitations):**
   - Animals crossing road
   - Stationary objects < 80 cm height
   - Oncoming traffic on undivided roads
```

### 03_verification.rst — SOTIF Verification and Validation

SOTIF requires two distinct verification/validation phases:

#### Area 2 Verification (§10)

Known scenarios with known causes — deterministic testing:

```rst
.. ver:: Sensor verification: radar range measurement accuracy
        tested with reference targets at 50 m, 100 m, 150 m, 200 m
        under clear, rain, and fog conditions.
   :id: VER_SOTIF_RANGE_TEST
   :tags: SOTIF;Area_2;sensor_verification;radar
   :links: REQ_SOTIF_PERCEP_001

   **Method:** ISO 21448 §10.2 — sensor verification
   **Environment:** Certified test track + weather simulation chamber
   **Target types:** Passenger car, motorcycle, pedestrian dummy
   **Samples per condition:** ≥100 measurements
   **Pass criteria:** Range accuracy ±5% or ±2 m (whichever larger);
                       no false negatives
```

#### Area 3 Validation (§11)

Unknown scenarios or unknown causes — statistical validation:

```rst
.. ver:: SOTIF validation: residual risk evaluation via
        scenario-based testing in simulation + real-world driving.
   :id: VER_SOTIF_VALIDATION
   :tags: SOTIF;Area_3;scenario_based;residual_risk
   :links: REQ_SOTIF_PERCEP_001;REQ_SOTIF_ALGO_001

   **Methodology:** ISO 21448 §11.2-§11.3
   **Simulation scenarios:** 10⁶ km equivalent (virtual)
   **Real-world validation:** 10⁵ km on public roads (mixed conditions)
   **Acceptance criteria:**
   - Residual risk < 10⁻⁷ fatalities per km (or equivalent)
   - No unknown hazardous scenarios discovered in last 5×10⁴ km of driving
   - False positive rate (unnecessary braking) < 10⁻⁴ per km

   **Scenario catalog:** See Annex F methodology — 1,200 scenarios
   derived from GIDAS/NDS accident databases + expert elicitation
```

#### Triggering Event Coverage

```rst
.. ver:: Triggering event coverage: all 47 identified triggering events
        (TE-001 through TE-047) have corresponding verification cases.
        Coverage: 47/47 (100%).
   :id: VER_SOTIF_TE_COVERAGE
   :tags: SOTIF;triggering_events;coverage
   :links: REQ_SOTIF_PERCEP_001;REQ_SOTIF_ALGO_001
```

### 07_safety_case.rst — SOTIF Safety Case

```rst
.. sc:: SOTIF claim: the automated driving system achieves
       acceptable residual risk for its ODD, with all identified
       triggering events addressed and no unknown hazardous
       scenarios remaining with unacceptable risk.
   :id: SC_SOTIF_TOP
   :tags: SOTIF;safety_case;release
   :links: SC_SOTIF_AREA2;SC_SOTIF_AREA3
   :collapsed: SC_SAFETY_TOP

.. sc:: Area 2: all known hazardous scenarios with known causes
       are verified as mitigated.
   :id: SC_SOTIF_AREA2
   :tags: SOTIF;Area_2
   :links: VER_SOTIF_RANGE_TEST;VER_SOTIF_TE_COVERAGE;SC_SOTIF_TOP

.. sc:: Area 3: residual risk from unknown scenarios is below
       the acceptable threshold, validated through scenario-based
       testing and real-world driving.
   :id: SC_SOTIF_AREA3
   :tags: SOTIF;Area_3
   :links: VER_SOTIF_VALIDATION;SC_SOTIF_TOP
```

### Lifecycle Management — SOTIF-Specific

```rst
.. lm:: SOTIF field monitoring: post-deployment data collection
       for continuous validation of residual risk assumptions.
       Trigger investigation if real-world incident rate exceeds
       predicted rate by 2σ.
   :id: LM_SOTIF_MONITORING
   :tags: SOTIF;field_monitoring;residual_risk
```

## ML/AI Perception — Beyond the Standard

ISO 21448:2022 provides a framework for ML-based perception but does
not specify ML-specific verification techniques. ISO PAS 8926 (AI functional
safety, draft) and ISO 8800 (in development) may address this gap.

Until then, document ML-specific concerns in OSQAr:

```rst
.. need:: The perception CNN shall be trained on a dataset covering
          all ODD conditions with class balance verified per
          ISO 21448 Annex D guidance.
   :id: REQ_SOTIF_ML_TRAINING
   :tags: SOTIF;ML;training_data;perception

   **Training set:** ≥10⁶ labelled frames
   **Class balance:** No class < 5% of total samples
   **Edge case coverage:** ≥1,000 samples per rare class
      (e.g., child, wheelchair, animal, debris)
   **Validation:** Hold-out test set from different geographic
      regions and weather conditions than training set
```

## Pitfalls

1. **Confusing SOTIF with functional safety** — SOTIF addresses performance
   limitations (the system works as designed); ISO 26262 addresses malfunctions
   (the system fails). They need separate analysis but coordinated integration.
2. **Scenario selection bias** — validating only common scenarios and missing
   rare-but-critical edge cases. Use accident database analysis + expert
   elicitation to identify long-tail scenarios.
3. **ML model drift** — a perception model validated in 2024 may behave
   differently in 2026 due to changing real-world conditions. Require
   continuous validation and define ODD boundaries conservatively.
4. **Over-reliance on simulation** — simulation can cover 10⁶ km but
   cannot discover unknown unknowns (by definition). Real-world validation
   remains essential.
5. **Acceptable risk ≠ zero risk** — SOTIF requires defining an acceptable
   residual risk threshold. This is an ethical and regulatory decision,
   not a purely technical one. Document the rationale.
6. **Failing to update the ODD** — if verification discovers limitations,
   narrow the ODD rather than accepting marginal performance.
