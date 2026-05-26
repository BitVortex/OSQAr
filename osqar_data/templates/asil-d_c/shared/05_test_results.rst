Test Results and Verification Evidence
======================================

This document aggregates test results, coverage measurements, static
analysis reports, and complexity analysis for the ASIL D qualification.

.. note::
   All evidence in this document MUST be generated from live tool runs,
   not hand-written. Use ``build-and-test.sh`` to execute the full
   verification pipeline.

.. csv-table:: Verification Activity Status
   :header: "Activity", "Status", "Tool", "Result", "Evidence"
   :widths: 30, 10, 20, 20, 20

   "Unit Tests", "Pending", "CMake/CTest", "—", "test_results.xml"
   "Statement Coverage", "Pending", "gcov/lcov", "—", "coverage_report.txt"
   "Branch Coverage", "Pending", "gcov/lcov", "—", "coverage_report.txt"
   "Static Analysis", "Pending", "cppcheck", "—", "cppcheck_report.xml"
   "Valgrind Memcheck", "Pending", "Valgrind", "—", "valgrind_report.txt"
   "Fuzzing (24h)", "Pending", "AFL++", "—", "fuzz_report.txt"
   "Compiler Warnings", "Pending", "GCC -Werror", "—", "build log"
   "Complexity", "Pending", "lizard", "—", "complexity_report.txt"
   "Reproducible Build", "Pending", "CMake+sha256sum", "—", "checksums"

Test Results
------------

.. test-results:: test_results.xml

Coverage Results
----------------

.. include:: ../coverage_report.txt
   :literal:

Static Analysis
---------------

.. include:: ../cppcheck_report.txt
   :literal:

Complexity Analysis
-------------------

.. include:: ../complexity_report.txt
   :literal:

.. include:: _static/gaps.rst
