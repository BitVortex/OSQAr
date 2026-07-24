ASIL Target Example (C)
=======================

This is an incomplete C SEooC example whose **target** is ASIL D. It shows how
standards claims can link to draft project requirements, architecture,
implementation, verification activities, and pending evidence. It does not
establish qualification, compliance, certification, or safety.

.. toctree::
   :maxdepth: 1

   00_standards_claims
   01_requirements
   02_architecture
   03_verification
   04_implementation
   05_test_results
   06_lifecycle_management

How to use this example
-----------------------

1. Build and test the C library with ``./build-and-test.sh test``.
2. Build the documentation with ``osqar build-docs``.
3. Inspect the ``STDCLAIM_*`` links as examples, not accepted conclusions.
4. Replace the catalog declarations, interpretations, requirements, criteria,
   and pending artifacts with project-authorized content.

Example status
--------------

* **Target:** ASIL D; not achieved by this scaffold.
* **Language:** C11.
* **Evidence:** placeholders remain pending.
* **Catalog:** the packaged ISO 26262 catalog is illustrative and incomplete.
