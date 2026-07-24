Evidence Placeholders
=====================

This document identifies expected verification artifacts for an example project
targeting ASIL D. Every record remains pending until the corresponding activity
has run and the project has captured provenance, result, and review state.

.. warning::

   Do not replace these placeholders with hand-written success claims. Generate
   artifacts from the selected project tools and process them through the
   controlled evidence-acceptance workflow.

Pending evidence records
------------------------

.. evid:: Unit-test result artifact
   :id: EVID_UNIT_TEST_RESULTS
   :status: draft
   :tags: ASIL_D;evidence;unit_test;pending
   :links: VER_UNIT_001

   Pending artifact expected at ``test_results.xml``. No execution result,
   provenance, review, or acceptance is asserted.

.. evid:: Structural-coverage result artifact
   :id: EVID_COVERAGE_REPORT
   :status: draft
   :tags: ASIL_D;evidence;coverage;pending
   :links: VER_COVERAGE_STMT;VER_COVERAGE_BRANCH;VER_COVERAGE_MCDC

   Pending artifact expected at ``coverage_report.txt``. No measurement,
   provenance, review, or acceptance is asserted. General branch or block
   coverage is not MC/DC proof.

.. csv-table:: Example verification status
   :header: "Activity", "State", "Method", "Result", "Expected artifact"
   :widths: 28, 12, 22, 16, 22

   "Unit tests", "Pending", "Project-selected test runner", "Not asserted", "test_results.xml"
   "Statement coverage", "Pending", "Project-selected coverage method", "Not asserted", "coverage_report.txt"
   "Branch coverage", "Pending", "Project-selected coverage method", "Not asserted", "coverage_report.txt"
   "Coding-standard analysis", "Pending", "Project-selected analyzer", "Not asserted", "static_analysis_report.txt"
   "Robustness/fuzzing", "Pending", "Project-selected campaign", "Not asserted", "fuzz_report.txt"
   "Compiler diagnostics", "Pending", "Accepted build configuration", "Not asserted", "build log"
   "Reproducible build", "Pending", "Project-defined comparison", "Not asserted", "checksums"

Test-result placeholder
-----------------------

.. test-results:: test_results.xml

Coverage placeholder
--------------------

.. include:: coverage_report.txt
   :literal:

Static-analysis placeholder
---------------------------

.. include:: static_analysis_report.txt
   :literal:

Complexity placeholder
----------------------

.. include:: complexity_report.txt
   :literal:

.. include:: _static/gaps.rst
