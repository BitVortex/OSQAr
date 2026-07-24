Getting Started
===============

This guide takes you from installation to a rendered OSQAr project and explains
what each step proves. Start with the generic scaffold; use the ASIL-target
examples only after you understand the basic evidence workflow.

What OSQAr gives you
====================

An OSQAr project is a documentation and evidence workspace. It can contain:

* structured requirements, architecture, verification, and lifecycle records;
* explicit links exported to machine-readable ``needs.json``;
* implementation, tests, reports, and project configuration;
* checksums and shipment metadata for transfer and archive.

OSQAr validates selected mechanical rules. It cannot determine technical
correctness, standards applicability, evidence sufficiency, safety, compliance,
certification, or qualification.

1. Install the CLI
==================

The lowest-friction installation uses ``pipx``::

   pipx install osqar
   osqar --help

For repository development, follow ``CONTRIBUTING.md`` and use the root
``./osqar`` wrapper.

2. Create a basic project
=========================

Choose the implementation language used by your project::

   osqar new --language rust --name first_osqar_project
   cd first_osqar_project

The default ``basic`` scaffold is intentionally small and standards-neutral.
Run ``osqar new --help`` to see templates available in the installed version.

3. Build and inspect
====================

Build the Sphinx documentation and open it::

   osqar build-docs
   osqar open-docs

The build produces rendered HTML and a ``needs.json`` export under ``_build``.
Inspect the generated pages and source RST files before changing them.

4. Author one controlled change
===============================

Open ``01_requirements.rst`` and replace an example requirement with a real,
uniquely identified project requirement. Then update the linked architecture or
verification record and rebuild::

   osqar build-docs

Stable identifiers are long-lived evidence addresses. Rename them only through
a controlled migration that also updates every inbound and outbound reference.

5. Run checks
=============

Run the checks selected by the project configuration::

   osqar doctor --project .

For an explicit traceability report::

   osqar traceability _build/html/needs.json \
     --json-report _build/html/traceability_report.json

A successful report means the executed rules passed for those bytes. It is not
a technical approval of the requirement or its links.

6. Prepare a shipment
=====================

When the project content and configured checks are ready for review::

   osqar shipment prepare --project . --archive

The command assembles the configured output and integrity data. Review its
reports and contents before transfer. The receiver should independently verify
the shipment; see :doc:`integrators_guide`.

Choose your next path
=====================

I want to learn from a richer example
-------------------------------------

Read :doc:`asil_examples`, then generate the C or Rust ASIL-target example.
Those examples show bounded links and pending evidence; they do not establish
qualification.

I produce evidence for another team
-----------------------------------

Continue with :doc:`suppliers_guide` and :doc:`ci_integration`.

I receive and combine evidence
------------------------------

Continue with :doc:`integrators_guide` and :doc:`multi_project_workflows`.

I need exact configuration or command behavior
----------------------------------------------

Use :doc:`configuration_and_hooks` and :doc:`cli_reference`.

I need strict evidence and qualification-profile semantics
----------------------------------------------------------

Use :doc:`evidence_acceptance`, :doc:`typed_traceability`, and
:doc:`tool_reliance_boundary`.
