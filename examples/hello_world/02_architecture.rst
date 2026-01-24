===================
System Architecture
===================

Component Architecture
======================

.. need:: (ARCH) The Thermal Sensor Interface Module (TSIM) shall consist of three components: Sensor Driver, Temperature Filter, and State Machine.
   :id: ARCH_001
   :status: active
   :tags: architecture, components
   :links: REQ_SAFETY_001, REQ_SAFETY_002, REQ_SAFETY_003

.. uml:: diagrams/01_component_architecture.puml
   :caption: TSIM Component Architecture - Links: :need:`ARCH_001`, :need:`ARCH_FUNC_001`, :need:`ARCH_FUNC_002`, :need:`ARCH_FUNC_003`
   :align: center

Data Flow & Timing
==================

.. uml:: diagrams/02_data_flow.puml
   :caption: TSIM Data Flow (Budget: :need:`REQ_SAFETY_002` @ 100ms) - Architecture: :need:`ARCH_FUNC_001`, :need:`ARCH_FUNC_002`, :need:`ARCH_FUNC_003`
   :align: center

The diagram above shows the complete data flow from sensor input through each processing stage, with timing allocations required by :need:`REQ_SAFETY_002`.

.. need:: (ARCH) The Sensor Driver shall read analog input at 100Hz sampling rate.
   :id: ARCH_FUNC_001
   :status: active
   :tags: sampling, timing
   :links: REQ_FUNC_001

   **Rationale**: 100Hz > 2× highest temperature change rate expected in any domain.
   
   **Tests**: :need:`TEST_CONVERSION_001`

.. need:: (ARCH) The Temperature Filter shall apply a 5-sample moving average before state evaluation.
   :id: ARCH_FUNC_002
   :status: active
   :tags: filtering, noise-rejection
   :links: REQ_FUNC_002

   **Tests**: :need:`TEST_FILTER_001`

.. need:: (ARCH) The State Machine shall evaluate temperature against thresholds and output state transitions within 50ms of detection.
   :id: ARCH_FUNC_003
   :status: active
   :tags: state-machine, timing, response
   :links: REQ_SAFETY_002, REQ_FUNC_003, REQ_FUNC_004

   **Timing Budget**: 50ms margin within 100ms requirement (:need:`REQ_SAFETY_002`).
   
   **Tests**: :need:`TEST_THRESHOLD_001`, :need:`TEST_HYSTERESIS_001`

Signal Definition
=================

.. need:: (ARCH) Raw Temperature Signal shall be a 12-bit analog input representing -40°C to +125°C.
   :id: ARCH_SIGNAL_001
   :status: active
   :tags: signal, input
   :links: REQ_FUNC_001

   **ADC Resolution**: 12-bit (4096 steps)
   
   **Range Mapping**:
   
   - 0 LSB → -40°C
   - 2048 LSB → 42.5°C
   - 4095 LSB → ~125°C
   
   **Tested by**: :need:`TEST_CONVERSION_001`

.. need:: (ARCH) Temperature Reading shall be a 16-bit signed integer in units of 0.1°C.
   :id: ARCH_SIGNAL_002
   :status: active
   :tags: signal, intermediate
   :links: REQ_FUNC_002

   **Range**: -400 to +1250 (representing -40.0°C to +125.0°C)
   
   **Tested by**: :need:`TEST_FILTER_001`

.. need:: (ARCH) State Output shall be a 1-bit signal: 0=SAFE, 1=UNSAFE.
   :id: ARCH_SIGNAL_003
   :status: active
   :tags: signal, output
   :links: REQ_SAFETY_002, REQ_SAFETY_003, REQ_FUNC_003, REQ_FUNC_004

   **Tested by**: :need:`TEST_THRESHOLD_001`, :need:`TEST_HYSTERESIS_001`

Error Handling
==============

.. need:: (ARCH) If sensor reading is invalid (out of physical bounds), the module shall remain in current state and log an error.
   :id: ARCH_ERROR_001
   :status: active
   :tags: error-handling, robustness
   :links: REQ_SAFETY_001

   **Rationale**: Conservative approach—hold last safe state rather than guess.

.. need:: (ARCH) The module shall track sensor read failures; after 10 consecutive failures, it shall enter UNSAFE state.
   :id: ARCH_ERROR_002
   :status: active
   :tags: error-handling, safety
   :links: REQ_SAFETY_002, REQ_SAFETY_003

   **Rationale**: Domain-agnostic fail-safe for sensor degradation (medical, industrial, automotive contexts).
   
   **Tested by**: :need:`TEST_FAIL_SAFE_001`

SEooC Boundary Definition
=========================

.. uml:: diagrams/03_domain_applicability.puml
   :caption: Domain-Agnostic SEooC Pattern - Architecture: :need:`ARCH_SEOOC_001`, :need:`ARCH_SEOOC_002`
   :align: center

.. need:: (ARCH) The TSIM shall be a Safety Element out of Context (SEooC) assuming the integrating system provides safe shutdown capability.
   :id: ARCH_SEOOC_001
   :status: active
   :tags: seooc, integration, safety-case
   :links: REQ_SAFETY_001, REQ_SAFETY_002

   **Integration Assumptions**:
   
   - Integrating system has verified shutdown mechanism
   - System controller responds to UNSAFE state within 1 second
   - Sensor hardware meets ±2°C accuracy
   - Operating environment is within -40°C to +80°C ambient
   
   **Domain Examples** (shown above):
   
   - **Medical**: Incubator/sterilizer temperature interlock (IEC 60601)
   - **Industrial**: Process control thermal limits (IEC 61508)
   - **Automotive**: Battery thermal management (ISO 26262)
   - **Robotics**: Motor overtemperature protection (ISO 13849)

.. need:: (ARCH) TSIM does not implement actual shutdown or corrective action; responsibility transfers to integrating system.
   :id: ARCH_SEOOC_002
   :status: active
   :tags: seooc, responsibility
   :links: ARCH_SEOOC_001, ARCH_001

   **Rationale**: Enables domain-agnostic reuse across medical (controlled environments), industrial (process control), robotics (motor shutdown), and automotive (powertrain management).
