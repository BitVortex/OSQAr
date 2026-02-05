OSQAr (Open Safety Qualification Architecture)
==============================================

OSQAr is a documentation-first framework for producing, verifying, and integrating **auditable evidence shipments** for safety/compliance work.

In OSQAr, a shipment is a reviewable bundle that contains **Sphinx documentation with maintained traceability**, plus the **implementation**, **tests**, and **analysis/verification reports** needed to review and audit the evidence end-to-end.

OSQAr is built on Sphinx + sphinx-needs and provides:

- requirements and traceability
- architecture diagrams (PlantUML)
- verification planning and traceability matrices
- evidence shipment workflows (integrity via checksum manifests)
- integrator-side multi-shipment intake with consolidated summaries
- lifecycle management guidance
- collaboration workflows for large, multi-user teams
- reproducible native builds for the C/C++/Rust example implementations (including optional Bazel integration)
- CI-produced demo shipments (documentation + traceability + implementation + tests + analysis reports + checksum manifests)

OSQAr also includes a small CLI for scaffolding new projects and running traceability/checksum verification.

Start here
==========

If you are new to OSQAr, a good first pass is:

1. Read the main entrypoint: :doc:`docs/using_the_boilerplate`.
2. Scaffold a minimal project and try a full build: :doc:`docs/project_setup_from_scratch`.
3. Then pick your role-specific workflow:

   - Supplier: :doc:`docs/suppliers_guide`
   - Integrator: :doc:`docs/integrators_guide`

.. toctree::
   :maxdepth: 1
   :caption: Framework
   :hidden:

   docs/using_the_boilerplate
   docs/project_setup_from_scratch
   docs/cli_reference

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
