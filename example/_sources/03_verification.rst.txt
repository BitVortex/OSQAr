==========================
Verification & Test Plan
==========================

Verification Strategy
=====================

.. need:: (TEST) Verification shall demonstrate that :need:`REQ_SAFETY_001`, :need:`REQ_SAFETY_002`, :need:`REQ_SAFETY_003`, and all functional requirements are met through unit tests and integration tests.
   :id: TEST_VERIFY_001
   :status: active
   :tags: v&v, strategy
   :links: REQ_SAFETY_001, REQ_SAFETY_002, REQ_SAFETY_003, REQ_FUNC_001, REQ_FUNC_002, REQ_FUNC_003, REQ_FUNC_004

Test Methods Overview
=====================

.. need:: (TEST) Unit tests shall verify individual components (:need:`ARCH_FUNC_001` Sensor Driver, :need:`ARCH_FUNC_002` Filter, :need:`ARCH_FUNC_003` State Machine) in isolation.
   :id: TEST_METHOD_001
   :status: active
   :tags: unit-test
   :links: ARCH_FUNC_001, ARCH_FUNC_002, ARCH_FUNC_003

.. need:: (TEST) Integration tests shall verify end-to-end data flow from sensor input to state output (:need:`ARCH_001` TSIM).
   :id: TEST_METHOD_002
   :status: active
   :tags: integration-test
   :links: TEST_METHOD_001, ARCH_001

.. need:: (TEST) Timing tests shall verify that all processing occurs within 100ms as specified in :need:`REQ_SAFETY_002`.
   :id: TEST_METHOD_003
   :status: active
   :tags: timing-test
   :links: REQ_SAFETY_002, ARCH_FUNC_003

Unit Test Cases
===============

.. need:: (TEST) TEST_CONVERSION_001: Sensor readings across full range (-40°C to +125°C) shall convert correctly per :need:`REQ_FUNC_001`.
   :id: TEST_CONVERSION_001
   :status: active
   :tags: unit-test, sensor-driver
   :links: REQ_FUNC_001, ARCH_FUNC_001, ARCH_SIGNAL_001

   **Test Steps**:
   
   1. Input ADC values: 0, 1024, 2048, 3072, 4095 LSB
   2. Verify output temperature: -40°C, -17.5°C, 42.5°C, 102.5°C, ~125°C
   
   **Pass Criteria**: All conversions within ±1°C accuracy
   
   **Architecture**: :need:`ARCH_FUNC_001`, :need:`ARCH_SIGNAL_001`

.. need:: (TEST) TEST_FILTER_001: Noise filtering with 5-sample moving average shall suppress sensor noise per :need:`REQ_FUNC_002`.
   :id: TEST_FILTER_001
   :status: active
   :tags: unit-test, filter
   :links: REQ_FUNC_002, ARCH_FUNC_002, ARCH_SIGNAL_002

   **Test Steps**:
   
   1. Input noisy sequence: [50, 60, 45, 55, 50, 48, 52, 49]°C
   2. After 5 samples, filter output shall stabilize around 50°C
   
   **Pass Criteria**: Noise amplitude reduced by ≥80%
   
   **Architecture**: :need:`ARCH_FUNC_002`, :need:`ARCH_SIGNAL_002`

.. need:: (TEST) TEST_THRESHOLD_001: State machine shall transition to UNSAFE when temperature ≥ 100°C per :need:`REQ_FUNC_003`.
   :id: TEST_THRESHOLD_001
   :status: active
   :tags: unit-test, state-machine
   :links: REQ_FUNC_003, REQ_SAFETY_002, ARCH_FUNC_003, ARCH_DESIGN_001

   **Test Steps**:
   
   1. Set initial state: SAFE (T=50°C)
   2. Inject temperature: 100°C
   3. Verify state output: UNSAFE
   
   **Pass Criteria**: State transition occurs on first call after threshold exceeded
   
   **Architecture**: :need:`ARCH_FUNC_003`, :need:`ARCH_DESIGN_001`

.. need:: (TEST) TEST_HYSTERESIS_001: State machine shall transition to SAFE only when temperature ≤ 95°C (hysteresis) per :need:`REQ_FUNC_004`.
   :id: TEST_HYSTERESIS_001
   :status: active
   :tags: unit-test, state-machine, hysteresis
   :links: REQ_FUNC_004, REQ_SAFETY_003, ARCH_DESIGN_001

   **Test Steps**:
   
   1. Set state: UNSAFE (T=100°C)
   2. Lower temperature to 99°C (still below hysteresis) → state remains UNSAFE
   3. Lower temperature to 95°C → state transitions to SAFE
   
   **Pass Criteria**: Hysteresis deadband prevents spurious oscillations

Integration Test Cases
======================

.. need:: (TEST) TEST_END_TO_END_001: Full sensor-to-state pipeline shall operate within latency budget per :need:`REQ_SAFETY_002`.
   :id: TEST_END_TO_END_001
   :status: active
   :tags: integration-test, timing
   :links: REQ_SAFETY_002, ARCH_001, ARCH_FUNC_003, TEST_METHOD_003

   **Test Steps**:
   
   1. Simulate analog sensor input ramping from 25°C to 105°C
   2. Measure time from input change to state output change
   
   **Pass Criteria**: End-to-end latency ≤ 50ms (margin within 100ms requirement)
   
   **Architecture**: :need:`ARCH_001`, :need:`ARCH_FUNC_003`

.. need:: (TEST) TEST_ERROR_RECOVERY_001: Module shall recover gracefully from persistent sensor errors per :need:`ARCH_ERROR_001`.
   :id: TEST_ERROR_RECOVERY_001
   :status: active
   :tags: integration-test, error-handling
   :links: ARCH_ERROR_001, REQ_SAFETY_001

   **Test Steps**:
   
   1. Inject invalid readings (<-50°C or >150°C range)
   2. Verify state remains unchanged for up to 9 errors
   3. Inject valid reading; verify normal operation resumes
   
   **Pass Criteria**: State unchanged during error sequence; recovery successful
   
   **Architecture**: :need:`ARCH_ERROR_001`

.. need:: (TEST) TEST_FAIL_SAFE_001: After 10 consecutive sensor failures, module shall enter UNSAFE state per :need:`ARCH_ERROR_002`.
   :id: TEST_FAIL_SAFE_001
   :status: active
   :tags: integration-test, fail-safe, safety
   :links: ARCH_ERROR_002, REQ_SAFETY_002, REQ_SAFETY_003

   **Test Steps**:
   
   1. Inject 10 consecutive invalid readings
   2. Verify state transitions to UNSAFE
   3. Confirm recovery pathway when valid readings resume
   
   **Pass Criteria**: UNSAFE state triggered; system alerts integrating system
   
   **Architecture**: :need:`ARCH_ERROR_002`, :need:`ARCH_SEOOC_001`

Traceability Matrix
===================

.. uml:: diagrams/04_traceability_matrix.puml
   :caption: Complete Requirements-to-Test Traceability - Architecture: :need:`ARCH_001` | Safety: :need:`REQ_SAFETY_001`, :need:`REQ_SAFETY_002`, :need:`REQ_SAFETY_003`
   :align: center

Detailed Traceability Table
===========================

.. list-table:: Requirements to Test Coverage
   :header-rows: 1
   :widths: 20 20 20 40

   * - Requirement
     - Test Case
     - Status
     - Coverage Notes

   * - :need:`REQ_SAFETY_001`
     - :need:`TEST_THRESHOLD_001`
     - Active
     - Safety goal foundation

   * - :need:`REQ_SAFETY_002`
     - :need:`TEST_THRESHOLD_001`, :need:`TEST_END_TO_END_001`
     - Active
     - Detects & reports within 100ms

   * - :need:`REQ_SAFETY_003`
     - :need:`TEST_HYSTERESIS_001`, :need:`TEST_FAIL_SAFE_001`
     - Active
     - Recovery & fail-safe behavior

   * - :need:`REQ_FUNC_001`
     - :need:`TEST_CONVERSION_001`
     - Active
     - Sensor reading accuracy (-40 to +125°C)

   * - :need:`REQ_FUNC_002`
     - :need:`TEST_FILTER_001`
     - Active
     - Noise filtering (≥80% reduction)

   * - :need:`REQ_FUNC_003`
     - :need:`TEST_THRESHOLD_001`
     - Active
     - Threshold detection at 100°C

   * - :need:`REQ_FUNC_004`
     - :need:`TEST_HYSTERESIS_001`
     - Active
     - Hysteresis deadband (95°C recovery)

   * - :need:`ARCH_FUNC_001`
     - :need:`TEST_CONVERSION_001`
     - Active
     - 100Hz sampling implementation

   * - :need:`ARCH_FUNC_002`
     - :need:`TEST_FILTER_001`
     - Active
     - 5-sample moving average

   * - :need:`ARCH_FUNC_003`
     - :need:`TEST_THRESHOLD_001`, :need:`TEST_HYSTERESIS_001`
     - Active
     - State machine logic

   * - :need:`ARCH_DESIGN_001`
     - :need:`TEST_THRESHOLD_001`, :need:`TEST_HYSTERESIS_001`
     - Active
     - Hysteresis state machine

   * - :need:`ARCH_ERROR_002`
     - :need:`TEST_FAIL_SAFE_001`
     - Active
     - Fail-safe error handling

Test Execution & Reporting
===========================

.. need:: (TEST) All unit tests shall execute in ≤ 1 second; integration tests in ≤ 5 seconds.
   :id: TEST_EXEC_001
   :status: active
   :tags: performance, ci-cd

.. need:: (TEST) Test results shall be exported in JUnit XML format for traceability reporting via sphinx-test-reports.
   :id: TEST_REPORT_001
   :status: active
   :tags: reporting, artifact

   **Integration**: Configure sphinx-test-reports in ``conf.py`` to import test results into this documentation for automated compliance artifact generation.
