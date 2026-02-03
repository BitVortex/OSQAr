=================================
Setting Up A Project From Scratch
=================================

This guide shows how to adopt OSQAr for a **new** component project or how to **migrate** an existing component into OSQAr.

The focus is practical:

- how to scaffold a project using the built-in OSQAr CLI
- where to copy your existing sources and tests
- how to migrate existing documentation into OSQAr’s traceable chapters
- how to ship the **next release** of a fictitious open-source library with an OSQAr evidence shipment

Prerequisites
=============

- Python + Poetry installed
- OSQAr available (either cloned from this repository, or vendored into your component repository)
- Your component has (or will have) automated tests that can emit **JUnit XML**

Install options
---------------

- Core docs + CLI (lean default)::

   poetry install

- Optional evidence tooling used by the example scripts (coverage + complexity)::

   poetry install --with evidence

Mental model
============

An OSQAr **project** is a Sphinx documentation project.
The output of building that project (typically ``_build/html``) becomes the **evidence shipment** directory that you archive and transfer.

A shipment is intended to be reviewable end-to-end and typically contains:

- rendered HTML documentation with traceability
- exported trace graph (``needs.json``)
- integrity manifest (``SHA256SUMS``)
- implementation sources and tests (for review/audit)
- raw verification outputs (e.g. ``test_results.xml``) and analysis reports

Step 1 — Choose a template and scaffold
=======================================

OSQAr ships a CLI that can copy a language template into a new project folder.

From the OSQAr repository root:

.. code-block:: bash

   # Example: create a new C-based component project
   poetry run python -m tools.osqar_cli new \
     --language c \
     --name OpenThermoLib \
     --destination ../OpenThermoLib

   cd ../OpenThermoLib

What you get
------------

The scaffolded project is a standalone Sphinx project with a familiar OSQAr chapter layout (requirements → architecture → verification → implementation → test results → lifecycle management).

Typical layout (simplified)::

   OpenThermoLib/
     conf.py
     index.rst
     01_requirements.rst
     02_architecture.rst
     03_verification.rst
     04_implementation.rst
     05_test_results.rst
     06_lifecycle_management.rst
     src/
     include/
     tests/
     build-and-test.sh

Step 2 — Copy your existing sources and tests
=============================================

If you are migrating an existing component, the simplest approach is:

- keep the component’s original repository as-is, but add OSQAr documentation at the repo root
- or create a new OSQAr-based repository and copy your code into it

Where to put code
-----------------

Follow the template conventions (they match the OSQAr example projects):

- **C**: ``src/`` + ``include/`` + ``tests/``
- **C++**: ``src/`` + ``include/`` + ``tests/``
- **Rust**: ``src/`` (Cargo crate) + ``tests/`` (or Rust integration tests) + ``Cargo.toml``
- **Python**: ``src/`` + ``tests/``

If your repository already uses different paths, you can keep them and simply adjust:

- the build script (e.g. ``build-and-test.sh``)
- the documentation chapter that references implementation locations

Tests and JUnit XML
-------------------

OSQAr’s example documentation can import JUnit XML.
Make sure your test run produces a stable file, commonly:

- ``test_results.xml`` at the project root

If you already produce JUnit XML elsewhere (e.g. ``build/test_results.xml``), either:

- copy it to ``test_results.xml`` as part of your build script, or
- adjust the Sphinx config / test report import paths in your project.

Step 3 — Migrate component documentation into OSQAr chapters
============================================================

Most existing open-source component documentation can be migrated by **splitting** it into OSQAr’s traceable chapters.

A practical mapping:

- ``README.md`` and design notes → ``02_architecture.rst``
- API reference snippets → ``04_implementation.rst``
- test plan / how-to-test → ``03_verification.rst``
- release notes / maintenance policy → ``06_lifecycle_management.rst``

Make requirements explicit
--------------------------

OSQAr is most valuable when you turn implicit expectations into explicit, traceable needs.

Example requirement (fictitious):

.. code-block:: rst

   .. need:: (FR) Convert raw sensor counts to temperature.
      :id: REQ_FUNC_CONVERT_001
      :status: active
      :links: ARCH_API_001, TEST_CONVERT_001

      The library shall convert ADC counts to degrees Celsius using a configurable calibration model.

Keep IDs stable and meaningful: once you ship a requirement ID in a release, treat it as a long-lived identifier.

Architecture and diagrams
-------------------------

If your project already has diagrams:

- export them to PlantUML where feasible
- store PlantUML sources under ``diagrams/`` and include them from RST

Example:

.. code-block:: rst

   .. uml:: diagrams/01_context.puml
      :caption: Context and boundaries

Verification chapter
--------------------

Use ``03_verification.rst`` to define *verification requirements* (``TEST_*``) and link them back to requirements/architecture.

Example:

.. code-block:: rst

   .. need:: (TEST) Conversion covers full ADC range.
      :id: TEST_CONVERT_001
      :status: active
      :links: REQ_FUNC_CONVERT_001

      Verification method: unit test.

Step 4 — Build an evidence shipment locally
===========================================

A minimal “supplier build” flow is:

1) run tests (produce ``test_results.xml``)
2) generate optional analysis reports (coverage/complexity)
3) build docs (exports ``needs.json``)
4) generate traceability report + checksums

If your project uses the provided script:

.. code-block:: bash

   poetry install --with evidence
   ./build-and-test.sh

If you prefer the CLI one-shot flow:

.. code-block:: bash

   poetry run python -m tools.osqar_cli supplier prepare \
     --project . \
     --clean \
     --archive

The shipped directory is typically ``_build/html``.

Worked example: shipping the next release of a fictitious library
=================================================================

Scenario
--------

Assume you maintain a fictitious open-source library:

- **Name:** OpenThermoLib
- **Purpose:** domain-agnostic temperature conversion + thresholding helper library
- **Language:** C
- **Next release:** ``v1.4.0``

Goal: ship ``v1.4.0`` together with an OSQAr evidence shipment.

Release checklist (supplier)
----------------------------

1) Freeze scope and update metadata
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- update your ``CHANGELOG.md``
- ensure requirement IDs are stable (do not rename IDs lightly)
- ensure tests are deterministic (no timestamps in JUnit XML if you can avoid it)

2) Produce a reproducible build
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Use the release commit timestamp for stable build metadata
   export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"

   # Build and collect evidence
   poetry install --with evidence
   OSQAR_REPRODUCIBLE=1 ./build-and-test.sh

3) Generate integrity metadata and a traceability report
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   poetry run python tools/traceability_check.py \
     _build/html/needs.json \
     --json-report _build/html/traceability_report.json

   poetry run python tools/generate_checksums.py \
     --root _build/html \
     --output _build/html/SHA256SUMS

   poetry run python tools/generate_checksums.py \
     --root _build/html \
     --verify _build/html/SHA256SUMS

4) Archive the shipment for distribution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Example naming convention
   tar -czf OpenThermoLib_v1.4.0_evidence_shipment.tar.gz -C _build html

   # Optional: verify checksums again after moving/copying the directory

5) Publish the release
^^^^^^^^^^^^^^^^^^^^^^

Common open-source pattern:

- create a git tag ``v1.4.0``
- create a GitHub Release
- attach:

  - the source archive (GitHub auto-generates)
  - ``OpenThermoLib_v1.4.0_evidence_shipment.tar.gz``

For higher assurance, consider signing the shipped checksum manifest externally (e.g., detached signature) and storing signatures separately.

Integrator-side intake (quick view)
-----------------------------------

An integrator who receives the shipment typically:

- verifies ``SHA256SUMS``
- optionally re-runs traceability checks on shipped ``needs.json``
- archives the shipment immutably

Example:

.. code-block:: bash

   poetry run python tools/generate_checksums.py \
     --root /path/to/OpenThermoLib_shipment \
     --verify /path/to/OpenThermoLib_shipment/SHA256SUMS

   poetry run python tools/traceability_check.py \
     /path/to/OpenThermoLib_shipment/needs.json \
     --json-report /path/to/OpenThermoLib_shipment/traceability_report.integrator.json

Next steps
==========

- If you need multi-supplier intake and consolidated reporting, see :doc:`multi_project_workflows`.
- For process discipline across releases (baselines, traceability evolution), see :doc:`lifecycle_management`.
