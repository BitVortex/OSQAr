OSQAr (Open Safety Qualification Architecture)
==============================================

OSQAr is a Sphinx + sphinx-needs boilerplate for producing auditable safety/compliance documentation artifacts:

- requirements and traceability
- architecture diagrams (PlantUML)
- verification planning and traceability matrices

OSQAr also includes a small CLI for scaffolding new projects and running traceability/checksum verification.

Start here:

.. toctree::
   :maxdepth: 2
   :caption: Documentation

   docs/using_the_boilerplate
   docs/lifecycle_management
   docs/integrators_guide
   docs/suppliers_guide
   docs/multi_project_workflows

.. toctree::
   :maxdepth: 1
   :caption: Examples

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

- ``examples/c_hello_world``
- ``examples/cpp_hello_world``
- ``examples/rust_hello_world``
- ``examples/python_hello_world``
