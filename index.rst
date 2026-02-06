OSQAr (Open Safety Qualification Architecture)
==============================================

OSQAr is a documentation-first framework for producing, verifying, and integrating **auditable evidence shipments** for safety/compliance work.

In OSQAr, a shipment is a reviewable bundle that contains **Sphinx documentation with maintained traceability**, plus the **implementation**, **tests**, and **analysis/verification reports** needed to review and audit the evidence end-to-end.

OSQAr is built on Sphinx + sphinx-needs and provides:

- structured requirements, architecture, and verification plans (via reStructuredText + sphinx-needs)
- traceability exports (``needs.json``), views (e.g., matrices), and audit-friendly reports
- architecture diagrams (PlantUML)
- evidence shipment workflows (documentation + evidence artifacts, integrity via checksum manifests)
- code trace checks (trace requirements/tests into code and validate consistency)
- integrator-side multi-shipment intake with consolidated summaries
- extensibility via project/workspace configuration (custom commands + hooks)
- lifecycle management guidance
- collaboration workflows for large, multi-user teams
- reproducible native builds for the C/C++/Rust example implementations (including optional Bazel integration)
- CI-produced demo shipments and release bundles (documentation + traceability + implementation + tests + analysis reports + checksum manifests)

OSQAr also includes a CLI for scaffolding new projects, building documentation, preparing/verifying shipments, and running traceability/checksum/code-trace checks.

Start here
==========

If you are new to OSQAr, a good first pass is:

1. Read the main entrypoint: :doc:`docs/using_the_boilerplate`.
2. Scaffold a minimal project and try a full build: :doc:`docs/project_setup_from_scratch`.
3. Then pick your role-specific workflow:

   - Supplier: :doc:`docs/suppliers_guide`
   - Integrator: :doc:`docs/integrators_guide`

Additional guides are linked in the sidebar.

.. toctree::
   :maxdepth: 1
   :caption: Framework
   :hidden:

   docs/using_the_boilerplate
   docs/project_setup_from_scratch
   docs/cli_reference
   docs/configuration_and_hooks

.. toctree::
   :maxdepth: 1
   :caption: Guides
   :hidden:

   docs/suppliers_guide
   docs/integrators_guide
   docs/lifecycle_management
   docs/multi_project_workflows
   docs/collaboration_workflows

.. toctree::
   :maxdepth: 1
   :caption: Examples
   :hidden:

   examples/index

Reference examples
==================

OSQAr is designed to support safety/compliance documentation for many technology stacks.

For **safety-related embedded** projects, OSQAr recommends using either **C** or **Rust** for the implementation and tests.

**C++** is a commonly used embedded language, but is typically harder to constrain (toolchain variability, language feature subset discipline, and qualification effort) and therefore is **not recommended** as a first choice.

The **Python** example is provided as an easy-to-run workstation demo for the documentation and traceability workflow; it is **not suited for embedded targets**.

Reference examples:

- `All examples index <examples/>`_
- `C example <examples/c/>`_
- `C++ example <examples/cpp/>`_
- `Rust example <examples/rust/>`_
- `Python demo example <examples/python/>`_
