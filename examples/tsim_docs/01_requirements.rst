================================
Safety & Functional Requirements
================================

Safety Goal
===========

.. need:: (SG) Prevent thermal damage by detecting abnormal temperature conditions and notifying the system to take corrective action.
   :id: REQ_SAFETY_001
   :status: active
   :tags: thermal, monitoring, safety-goal
   :links: ARCH_001, ARCH_SEOOC_001

Safety Requirements
===================

.. need:: (SR) The system shall detect when temperature exceeds the safe operating limit and report an unsafe state within 100ms.
   :id: REQ_SAFETY_002
   :status: active
   :tags: thermal, detection, timing
   :links: REQ_SAFETY_001, ARCH_FUNC_003, ARCH_SIGNAL_003
   
   **Rationale**: Timely detection enables corrective action before damage occurs.
   
   **Architecture**: :need:`ARCH_FUNC_003`
   
   **Tests**: :need:`TEST_END_TO_END_001`

.. need:: (SR) The system shall report a safe state when temperature returns to normal operating range.
   :id: REQ_SAFETY_003
   :status: active
   :tags: thermal, recovery
   :links: REQ_SAFETY_001, ARCH_ERROR_002, ARCH_SIGNAL_003

   **Rationale**: Clear state transitions enable predictable system behavior.
   
   **Architecture**: :need:`ARCH_ERROR_002`
   
   **Tests**: :need:`TEST_FAIL_SAFE_001`

Functional Requirements
=======================

.. need:: (FR) The module shall read analog sensor input and convert it to temperature in degrees Celsius.
   :id: REQ_FUNC_001
   :status: active
   :tags: sensor, conversion
   :links: REQ_SAFETY_002, ARCH_FUNC_001, ARCH_SIGNAL_001

   **Output Range**: -40°C to +125°C (covers medical, industrial, automotive domains)
   
   **Architecture**: :need:`ARCH_FUNC_001`, :need:`ARCH_SIGNAL_001`, :need:`ARCH_SIGNAL_002`
   
   **Tests**: :need:`TEST_CONVERSION_001`

.. need:: (FR) The module shall filter sensor noise using a 5-sample moving average.
   :id: REQ_FUNC_002
   :status: active
   :tags: filtering, stability
   :links: REQ_SAFETY_002, ARCH_FUNC_002, ARCH_SIGNAL_002

   **Rationale**: Prevents spurious state changes from sensor noise.
   
   **Architecture**: :need:`ARCH_FUNC_002`
   
   **Tests**: :need:`TEST_FILTER_001`

.. need:: (FR) The module shall trigger a safe state alert when temperature ≥ 100°C (configurable threshold).
   :id: REQ_FUNC_003
   :status: active
   :tags: threshold, alert
   :links: REQ_SAFETY_002, ARCH_FUNC_003, ARCH_DESIGN_001

   **Architecture**: :need:`ARCH_FUNC_003`, :need:`ARCH_DESIGN_001`
   
   **Tests**: :need:`TEST_THRESHOLD_001`

.. need:: (FR) The module shall trigger a recovery to normal state when temperature ≤ 95°C (hysteresis).
   :id: REQ_FUNC_004
   :status: active
   :tags: threshold, hysteresis, recovery
   :links: REQ_SAFETY_003, ARCH_DESIGN_001

   **Rationale**: 5°C hysteresis prevents oscillation at threshold boundary.
   
   **Architecture**: :need:`ARCH_DESIGN_001`
   
   **Tests**: :need:`TEST_HYSTERESIS_001`

Design Specifications
=====================

.. need:: (ARCH) Temperature monitoring shall be implemented as a state machine with two states: SAFE and UNSAFE.
   :id: ARCH_DESIGN_001
   :status: active
   :tags: architecture, state-machine
   :links: REQ_FUNC_003, REQ_FUNC_004, ARCH_FUNC_003

   **States**:
   
   - **SAFE**: Temperature within safe range (< 95°C)
   - **UNSAFE**: Temperature exceeds threshold (≥ 100°C)
   
   **Implementation**: :need:`CODE_IMPL_001`
   
   **Tests**: :need:`TEST_THRESHOLD_001`, :need:`TEST_HYSTERESIS_001`

.. need:: (ARCH) The module shall store the last valid temperature reading and timestamp.
   :id: ARCH_DESIGN_002
   :status: active
   :tags: data, state
   :links: REQ_FUNC_001, ARCH_SIGNAL_002

.. need:: (ARCH) All temperature thresholds shall be stored in read-only configuration registers.
   :id: ARCH_DESIGN_003
   :status: active
   :tags: configuration, safety
   :links: REQ_FUNC_003, REQ_FUNC_004

   **Rationale**: Prevents accidental or malicious threshold modification during operation.

Test Coverage Mapping
=====================

.. need:: REQ_SAFETY_002 shall be verified by TEST_DETECTION_001 and TEST_TIMING_001.
   :id: TRACE_TEST_001
   :status: active
   :tags: traceability

.. need:: REQ_FUNC_003 shall be verified by TEST_THRESHOLD_001.
   :id: TRACE_TEST_002
   :status: active
   :tags: traceability
