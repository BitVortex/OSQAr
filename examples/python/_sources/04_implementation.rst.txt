==========================
Implementation & Test Code
==========================

Code Organization
=================

The TSIM implementation demonstrates traceability from requirements through architecture to code and tests.

.. code-block:: text

  examples/python_hello_world/
    ├── src/
    │   ├── __init__.py
    │   └── tsim.py              # Implementation with requirement IDs as docstring comments
    ├── tests/
    │   ├── __init__.py
    │   └── test_tsim.py         # Test cases linked to TEST_* requirements
    └── test_results.xml         # JUnit XML for sphinx-test-reports integration

Implementation Traceability
===========================

All code modules include requirement traceability in docstrings and comments. Click on requirement IDs below to navigate to their definitions:

.. need:: (CODE) Implementation follows requirement IDs and architecture specifications.
   :id: CODE_IMPL_001
   :status: active
   :tags: implementation, code, traceability
   :links: ARCH_001, ARCH_FUNC_001, ARCH_FUNC_002, ARCH_FUNC_003

   Each Python module, class, and function includes docstring comments mapping to:
   
   - Safety Requirements (:need:`REQ_SAFETY_001`, :need:`REQ_SAFETY_002`, :need:`REQ_SAFETY_003`)
   - Functional Requirements (:need:`REQ_FUNC_001`, :need:`REQ_FUNC_002`, :need:`REQ_FUNC_003`, :need:`REQ_FUNC_004`)
   - Architecture Specifications (:need:`ARCH_001`, :need:`ARCH_FUNC_001`, :need:`ARCH_FUNC_002`, :need:`ARCH_FUNC_003`, :need:`ARCH_DESIGN_001`)

Example: Sensor Driver Implementation
======================================

The ``SensorDriver`` class implements :need:`REQ_FUNC_001` (ADC conversion) as specified in :need:`ARCH_FUNC_001`:

.. code-block:: python
   :linenos:

   class SensorDriver:
       """
       ADC Sensor Input Driver
       
       Traceability:
         - ARCH_FUNC_001: 100Hz sampling rate
         - REQ_FUNC_001: ADC to temperature conversion
         - ARCH_SIGNAL_001: 12-bit ADC input
         - ARCH_SIGNAL_002: 16-bit signed output
       """
       
       def read_adc(self, adc_counts: int) -> int:
           """
           Read ADC value and convert to temperature.
           
           Traceability:
               TEST_CONVERSION_001: Validates conversion
               REQ_FUNC_001: Conversion requirement
           """
           # Linear interpolation: ADC counts → Celsius
           celsius = (
               self.ADC_MIN_CELSIUS +
               (adc_counts - self.ADC_MIN_COUNTS) *
               (self.ADC_MAX_CELSIUS - self.ADC_MIN_CELSIUS) /
               (self.ADC_MAX_COUNTS - self.ADC_MIN_COUNTS)
           )
           # ...

**Linked Requirements**: :need:`REQ_FUNC_001`, :need:`ARCH_FUNC_001`, :need:`ARCH_SIGNAL_001`, :need:`ARCH_SIGNAL_002`

State Machine Example
=====================

The ``StateMachine`` class implements :need:`REQ_FUNC_003` and :need:`REQ_FUNC_004` (threshold & hysteresis) as specified in :need:`ARCH_DESIGN_001`:

.. code-block:: python
   :linenos:

   class StateMachine:
       """
       Temperature state machine with hysteresis.
       
       Traceability:
         - ARCH_DESIGN_001: State machine architecture
         - REQ_SAFETY_002: Detect within 100ms
         - REQ_FUNC_003: Threshold detection
         - REQ_FUNC_004: Hysteresis recovery
       """
       
       def evaluate(self, temperature: int) -> TemperatureState:
           """
           Evaluate temperature with hysteresis.
           
           Traceability:
               TEST_THRESHOLD_001: Threshold at 100°C
               TEST_HYSTERESIS_001: Hysteresis at 95°C
           """
           high_threshold = int(round(self.config.threshold_high_celsius * 10.0))
           low_threshold = int(round(self.config.threshold_low_celsius * 10.0))
           
           if self.state == TemperatureState.SAFE:
               if temperature >= high_threshold:
                   self.state = TemperatureState.UNSAFE
           elif self.state == TemperatureState.UNSAFE:
               if temperature <= low_threshold:
                   self.state = TemperatureState.SAFE
           
           return self.state

Test Suite Mapping
==================

.. need:: (TEST) Test suite provides complete coverage of requirements.
   :id: TEST_CODE_001
   :status: active
   :tags: verification, testing, code

   **Test Coverage Matrix**:
   
   - **TestSensorDriver**: Tests ARCH_FUNC_001, REQ_FUNC_001
     - `test_conversion_full_range` → TEST_CONVERSION_001
     - `test_conversion_accuracy` → TEST_CONVERSION_001
   
   - **TestTemperatureFilter**: Tests ARCH_FUNC_002, REQ_FUNC_002
     - `test_filter_noise_rejection` → TEST_FILTER_001
     - `test_filter_stabilization` → TEST_FILTER_001
   
   - **TestStateMachine**: Tests ARCH_DESIGN_001, REQ_FUNC_003/004
     - `test_threshold_detection` → TEST_THRESHOLD_001
     - `test_hysteresis_deadband` → TEST_HYSTERESIS_001
     - `test_state_output_bit` → ARCH_SIGNAL_003
   
   - **TestTSIMIntegration**: Tests end-to-end ARCH_001
     - `test_end_to_end_latency` → TEST_END_TO_END_001
     - `test_detection_within_100ms` → TEST_END_TO_END_001
     - `test_safe_state_recovery` → REQ_SAFETY_003
     - `test_error_recovery` → TEST_ERROR_RECOVERY_001
     - `test_fail_safe_on_persistent_errors` → TEST_FAIL_SAFE_001
   
   **Total**: 13 test cases covering 20+ requirements

Test Execution & Reporting
===========================

.. code-block:: bash

   # Run tests with verbose output
  cd examples/python_hello_world
   poetry run pytest tests/test_tsim.py -v
   
   # Generate JUnit XML for compliance reporting
   poetry run pytest tests/test_tsim.py --junit-xml=test_results.xml
   
   # Results can be imported by sphinx-test-reports for automated traceability

Test Results Integration
========================

The generated ``test_results.xml`` can be integrated into Sphinx documentation via sphinx-test-reports:

.. code-block:: python
   :caption: conf.py configuration for test result integration

   # Configure sphinx-test-reports
   test_reports = {
       'junit': {
           'path': 'test_results.xml',
           'requirement_mapping': {
               'TEST_CONVERSION_001': 'REQ_FUNC_001',
               'TEST_FILTER_001': 'REQ_FUNC_002',
               'TEST_THRESHOLD_001': 'REQ_FUNC_003',
               # ... map all tests to requirements
           }
       }
   }

Building the Full Chain
=======================

The complete traceability chain flows:

.. code-block:: text

   ISO 26262 Safety Goal (REQ_SAFETY_001)
            ↓
   Safety Requirements (REQ_SAFETY_002/003)
            ↓
   Functional Requirements (REQ_FUNC_001-004)
            ↓
   Architectural Design (ARCH_FUNC_001-003, ARCH_DESIGN_001)
            ↓
   Implementation Code (src/tsim.py)
            ↓
   Unit Tests (tests/test_tsim.py)
            ↓
   Test Results (test_results.xml)
            ↓
   Documentation (index.rst, *.rst)
            ↓
   Compliance Artifacts (HTML with traceability matrix)

Code Repository Structure
==========================

.. need:: (CODE) Complete example includes both documentation and implementation.
   :id: CODE_REPO_001
   :status: active
   :tags: repository, structure

   **File Listing**:
   
   - `01_requirements.rst` - Requirements specification
   - `02_architecture.rst` - Architecture with diagrams
   - `03_verification.rst` - Verification plan and traceability matrix
   - `**04_implementation.rst**` - This file (code examples and test mapping)
   - `conf.py` - Sphinx configuration
   - `diagrams/` - PlantUML architecture diagrams
   - `src/tsim.py` - Implementation with traceability comments
   - `tests/test_tsim.py` - Comprehensive test suite
   - `test_results.xml` - JUnit test results

Extending the Example
=====================

To add more domains or features:

1. **Add new requirements** to `01_requirements.rst`
2. **Update architecture** in `02_architecture.rst` and `diagrams/`
3. **Extend implementation** in `src/tsim.py` with domain-specific code
4. **Add tests** in `tests/test_tsim.py` mapped to new test requirements
5. **Rebuild documentation**: `sphinx-build -b html . _build/html`
6. **Run tests**: `pytest tests/ --junit-xml=test_results.xml`
7. **Verify traceability**: Check generated HTML matrix

This demonstrates how OSQAr enables **complete compliance verification** from high-level safety goals through low-level code and automated test reporting—all traceable in the generated documentation.
