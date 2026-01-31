==============================
Test Results & Traceability
==============================

Overview
========

This section demonstrates how OSQAr auto-imports test results into the documentation, establishing a complete **compliance artifact chain** from safety goals through implementation code to automated test reporting.

The traceability flow is:

.. code-block:: text

    ISO 26262 Safety Goal
         ↓
    Safety Requirement (REQ_SAFETY_*)
         ↓
    Functional Requirement (REQ_FUNC_*, ARCH_*)
         ↓
        Implementation Code (src/* with requirement IDs)
         ↓
        Unit Tests (tests/* with TEST_* IDs)
         ↓
    JUnit XML Test Results
         ↓
    Sphinx Auto-Import & HTML Report
         ↓
    Compliance Artifact Package

Test Suite Execution
====================

The test suite can be run locally to generate compliance artifacts:

.. code-block:: bash

  # Pick one language example and run its end-to-end script.
  # This generates JUnit XML + builds HTML docs with imported test results.
  cd examples/<language>_hello_world
  ./build-and-test.sh

  # The generated docs live under the example directory.
  open _build/html/index.html

Test Configuration File
=======================

The test results are automatically imported via Sphinx configuration:

.. code-block:: python

    # conf.py configuration
    extensions = [
      'sphinx_needs',                 # Requirements traceability
      'sphinxcontrib.test_reports',   # Auto-import JUnit XML
      'sphinxcontrib.plantuml',       # Diagrams
    ]
    
    # Point to the JUnit XML file
    test_reports = ['test_results.xml']

This configuration tells Sphinx to parse ``test_results.xml`` and create a searchable, linked test report within the documentation.

Test Requirements Mapping
==========================

This section describes how each test requirement maps to implementation code and safety/functional requirements. All TEST_* needs are defined in the :doc:`03_verification` document; this section provides the execution results and detailed traceability analysis.

**Key Points**:

- TEST_CONVERSION_001 (:need:`TEST_CONVERSION_001`): Sensor Driver Tests
- TEST_FILTER_001 (:need:`TEST_FILTER_001`): Filter Noise Rejection  
- TEST_THRESHOLD_001 (:need:`TEST_THRESHOLD_001`): Threshold Detection
- TEST_HYSTERESIS_001 (:need:`TEST_HYSTERESIS_001`): Hysteresis Deadband
- TEST_END_TO_END_001 (:need:`TEST_END_TO_END_001`): End-to-End Latency
- TEST_FAIL_SAFE_001 (:need:`TEST_FAIL_SAFE_001`): Fail-Safe on Persistent Errors

See :doc:`03_verification` for detailed test case specifications and acceptance criteria.

Traceability Matrix
===================

The following matrix demonstrates the complete traceability chain from requirements through code to tests. All IDs are clickable hyperlinks to requirement definitions:

.. list-table:: Requirement-to-Test Traceability
   :header-rows: 1
   :widths: 20 25 20 35

   * - Requirement ID
     - Requirement Description
     - Test Case(s)
     - Code Implementation

   * - :need:`REQ_SAFETY_001`
     - Prevent thermal damage to equipment
     - :need:`TEST_THRESHOLD_001`, :need:`TEST_END_TO_END_001`
     - ``StateMachine.evaluate()`` (:need:`ARCH_FUNC_003`)

   * - :need:`REQ_SAFETY_002`
     - Detect overheat within 100ms
     - :need:`TEST_END_TO_END_001`
     - ``TSIM.process_sample()`` (:need:`ARCH_001`)

   * - :need:`REQ_SAFETY_003`
     - Report safe state recovery reliably
     - :need:`TEST_FAIL_SAFE_001`
     - ``StateMachine.evaluate()`` (:need:`ARCH_FUNC_003`)

   * - :need:`REQ_FUNC_001`
     - Convert 12-bit ADC to 0.1°C units
     - :need:`TEST_CONVERSION_001`
     - ``SensorDriver.read_adc()`` (:need:`ARCH_FUNC_001`)

   * - :need:`REQ_FUNC_002`
     - Filter sensor noise (≥80% reduction)
     - :need:`TEST_FILTER_001`
     - ``TemperatureFilter.update()`` (:need:`ARCH_FUNC_002`)

   * - :need:`REQ_FUNC_003`
     - Detect 100°C threshold
     - :need:`TEST_THRESHOLD_001`
     - ``StateMachine.evaluate()`` (:need:`ARCH_FUNC_003`)

   * - :need:`REQ_FUNC_004`
     - Apply 5°C hysteresis deadband
     - :need:`TEST_HYSTERESIS_001`
     - ``StateMachine`` with :need:`ARCH_DESIGN_001`

   * - :need:`ARCH_FUNC_001`
     - Sensor driver component (100Hz sampling)
     - :need:`TEST_CONVERSION_001`
     - 5 class methods in ``SensorDriver``

   * - :need:`ARCH_FUNC_002`
     - Filter component (5-sample MA)
     - :need:`TEST_FILTER_001`
     - 3 class methods in ``TemperatureFilter``

   * - :need:`ARCH_FUNC_003`
     - State machine component (hysteresis)
     - :need:`TEST_THRESHOLD_001`, :need:`TEST_HYSTERESIS_001`
     - 4 class methods in ``StateMachine``

   * - :need:`ARCH_DESIGN_001`
     - Hysteresis state machine (100°C/95°C thresholds)
     - :need:`TEST_HYSTERESIS_001`
     - ``StateMachine`` class with ``TemperatureConfig``

   * - :need:`ARCH_ERROR_002`
     - Fail-safe error handling (10-error threshold)
     - :need:`TEST_FAIL_SAFE_001`
     - Error counter in ``ThermalSensorInterfaceModule``

Automated Test Reporting
==========================

The JUnit XML output from your test runner (pytest for the Python example, or a native runner for C/C++/Rust) is automatically processed by Sphinx:

.. code-block:: xml

    <testsuite>
      <testcase classname="tests.test_tsim.TestSensorDriver" 
                 name="test_conversion_full_range" time="0.002">
      </testcase>
      <!-- mapped to TEST_CONVERSION_001 requirement -->
    </testsuite>

This XML is parsed and linked to requirements using the test case names (mapped through docstrings to TEST_* IDs). The resulting HTML documentation includes:

1. **Test Results Table**: Lists all test cases with pass/fail status
2. **Requirement Links**: Each test linked to its corresponding requirement
3. **Execution Metadata**: Timing, host, and result details
4. **Traceability Queries**: Search and filter tests by requirement ID

Building Compliance Artifacts
==============================

The complete compliance artifact package is generated via:

.. code-block:: bash

  # 1. Run tests, emit JUnit XML, build docs
  cd examples/<language>_hello_world
  ./build-and-test.sh

  # 2. Output contains:
  #    - Linked requirements and tests
  #    - Architecture diagrams with PlantUML
  #    - Test results integrated into HTML
  #    - Searchable traceability matrix
  #    - Compliance documentation suitable for assessment/audit

Domain-Agnostic Test Strategy
=============================

The test suite is designed to work across all supported domains (medical, automotive, robotics, industrial) because:

1. **Tests are functional, not domain-specific**: All tests verify sensor conversion, filtering, and threshold logic without domain assumptions
2. **Safety requirements are domain-agnostic**: REQ_SAFETY_* and REQ_FUNC_* refer to generic overheat detection, not domain-specific hazards
3. **ASIL assignment is domain-specific**: The domain integrator assigns ASIL (Automotive Safety Integrity Level) or equivalent:
   
   - **Medical**: Critical → ASIL-C equivalent, requires fault injection testing
   - **Automotive**: High → ASIL-C, requires functional safety manager review
   - **Robotics**: Medium → ASIL-B equivalent, requires scenario testing
   - **Industrial**: Low-Medium → ASIL-B equivalent, requires HAZOP analysis

4. **Test coverage scales with domain**: Additional tests added per domain for specific failure modes (e.g., medical sensor calibration drift, automotive temperature shock resilience)

Extending the Test Suite
=========================

To add domain-specific tests:

1. **Create domain directory**: ``examples/<your_domain_or_product>/``
2. **Implement tests** in the language of your product and ensure the runner emits JUnit XML.
3. **Use stable IDs**: keep requirement IDs (``REQ_*``, ``ARCH_*``) and test IDs (``TEST_*``) consistent so the traceability graph remains intact.
4. **Update documentation**: link domain-specific tests to domain-specific requirements (e.g., ``REQ_MEDICAL_SAFETY_001``).
5. **Rebuild**: Sphinx imports results and updates traceability.


Compliance Artifact Checklist
=============================

Use this checklist to verify complete traceability when qualifying per ISO 26262:

.. code-block:: text

    [✓] Requirements documented with needs IDs (REQ_*, ARCH_*)
    [✓] Architecture diagrams with PlantUML (SVG format)
    [✓] Implementation code with requirement docstrings
    [✓] Test suite with TEST_* IDs mapped to requirements
    [✓] JUnit XML test results generated
    [✓] Sphinx imports test results into documentation
    [✓] HTML documentation includes traceability matrix
    [✓] All requirements have ≥1 test case
    [✓] All test cases linked to ≥1 requirement
    [✓] No orphaned requirements (untested, unimplemented)
    [✓] No orphaned tests (unlinked to requirements)
    [✓] Build succeeds without errors
    [✓] HTML documentation is searchable and indexed

Next Steps
==========

1. **Configure CI/CD**: Add GitHub Actions to auto-run tests and rebuild documentation on commits
2. **Add Domain Examples**: Create medical_device, automotive, robotics subdirectories with domain-specific requirements
3. **Extend Test Coverage**: Add performance benchmarks, fault injection tests, environmental stress tests
4. **Implement Requirements Gateway**: Create automated checks that fail builds if requirements lack tests
