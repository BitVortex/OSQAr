==================================
Getting Started with OSQAr
==================================

If you're new to OSQAr, this page gets you from zero to your first auditable evidence shipment in about five minutes.

What OSQAr is
=============

OSQAr is a **documentation-first framework** for producing, verifying, and integrating **auditable evidence shipments** for safety/compliance work.

Think of it as "CI for traceability": you write structured requirements and architecture in reStructuredText, link them together with ``sphinx-needs``, run verification checks, and package everything into an integrity-protected shipment that an integrator or auditor can verify independently.

**One command to ship:**

.. code-block:: console

   osqar shipment prepare --project . --archive

This builds your docs, runs traceability checks, generates checksums, and creates a ZIP archive — all in one shot.

Install
=======

OSQAr is a Python package. Install it once:

.. code-block:: console

   pipx install osqar
   osqar --help

Build your first shipment
=========================

Scaffold a project, write one requirement, build:

.. code-block:: console

   # 1. Create a new C project
   osqar new --language c --name hello_safety --destination .

   # 2. Build the documentation with traceability
   cd hello_safety
   osqar build-docs

   # 3. Open it in your browser
   osqar open-docs

That's it — you have rendered documentation with a traceability graph, a ``needs.json`` export, and PlantUML diagram support.

For a full end-to-end run including test execution and evidence reports, check out the reference examples:

.. code-block:: console

   cd examples/python_hello_world
   ./build-and-test.sh
   osqar shipment prepare --project . --archive

Where to go next
================

**By role:**

- :doc:`suppliers_guide` — produce auditable evidence shipments for a component
- :doc:`integrators_guide` — verify, intake, and integrate received shipments
- :doc:`ci_integration` — wire OSQAr into GitHub Actions or your CI pipeline

**In depth:**

- :doc:`using_the_boilerplate` — comprehensive guide: mental model, terms, copy/paste workflow recipes
- :doc:`project_setup_from_scratch` — scaffold a new project or migrate an existing one
- :doc:`cli_reference` — full per-command reference (all flags, exit codes, examples)

**Real-world demonstration:**

- `OSQAr-cJSON <https://github.com/BitVortex/OSQAr-cJSON>`_ — an ISO 26262 SEooC qualification attempt of the cJSON library using OSQAr, targeting ASIL D, with CI-driven evidence shipments and 88% statement coverage.
