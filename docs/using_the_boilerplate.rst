=============================
Using the OSQAr Boilerplate
=============================

Purpose
=======

OSQAr is a **documentation-first** boilerplate for producing auditable safety/compliance artifacts with:

- structured requirements and traceability (via ``sphinx-needs``)
- architecture diagrams (via PlantUML)
- verification planning and traceability (requirements ↔ architecture ↔ tests)

Quick start
===========

Build the rendered HTML documentation from the repository root:

.. code-block:: bash

   poetry install
   poetry run sphinx-build -b html . _build/html
   open _build/html/index.html

Reference examples (C/C++/Rust)
===============================

OSQAr primarily targets **C**, **C++**, and **Rust** projects.

Each example produces:

- native test results as `test_results.xml` (JUnit)
- rendered HTML documentation that can import the JUnit results (via `sphinx-test-reports`)

Build any example documentation directly:

.. code-block:: bash

   poetry install
   poetry run sphinx-build -b html examples/c_hello_world _build/html/example
   poetry run sphinx-build -b html examples/cpp_hello_world _build/html/examples/cpp
   poetry run sphinx-build -b html examples/rust_hello_world _build/html/examples/rust

Run an end-to-end workflow (native tests → docs) for an example:

.. code-block:: bash

   cd examples/c_hello_world
   ./build-and-test.sh
   open _build/html/index.html

Legacy Python reference
=======================

The original Python example remains available as a documentation/reference variant:

.. code-block:: bash

   cd examples/hello_world
   ./build-and-test.sh
   open _build/html/index.html

Core workflow
=============

OSQAr works best when you keep a consistent structure:

- define requirements and constraints as ``.. need::`` objects with stable IDs
- link requirements ↔ architecture ↔ tests using ``:links:`` and ``:need:`ID``` references
- keep architecture diagrams in PlantUML sources under version control
- define verification requirements (``TEST_*``) and provide a traceability matrix

Writing requirements (sphinx-needs)
===================================

A requirement is defined using a ``.. need::`` directive with a stable ``:id:``.

.. code-block:: rst

   .. need:: (SR) Detect overheat within 100ms.
      :id: REQ_SAFETY_002
      :status: active
      :tags: timing
      :links: REQ_SAFETY_001, ARCH_FUNC_003, TEST_END_TO_END_001

      **Architecture**: :need:`ARCH_FUNC_003`
      **Tests**: :need:`TEST_END_TO_END_001`

Recommended ID scheme
=====================

The boilerplate enforces ID discipline via ``needs_id_regex``.

A practical scheme is:

- ``REQ_SAFETY_*``: safety goals and safety requirements
- ``REQ_FUNC_*``: functional requirements
- ``ARCH_*``: architecture/design constraints and interfaces
- ``TEST_*``: verification requirements / test specifications

Architecture diagrams (PlantUML)
================================

PlantUML sources live in ``diagrams/`` and are included from RST:

.. code-block:: rst

   .. uml:: diagrams/02_data_flow.puml
      :caption: Data flow (budget: :need:`REQ_SAFETY_002`) — Architecture: :need:`ARCH_FUNC_001`, :need:`ARCH_FUNC_002`, :need:`ARCH_FUNC_003`

Verification and traceability
=============================

A robust verification chapter typically contains:

1) test requirements as needs objects (``TEST_*``)
2) a traceability matrix mapping ``REQ_*``/``ARCH_*`` → ``TEST_*``

Code complexity (optional)
==========================

OSQAr supports generating additional *engineering evidence* artifacts alongside test results.

All reference examples include an optional **code complexity report** step that produces
``complexity_report.txt``.

- **C / C++ / Python**: `lizard <https://github.com/terryyin/lizard>`_ (Cyclomatic Complexity)
   - Runs as part of the example scripts via ``poetry run lizard``.
   - You can run it manually from the repository root, e.g.:

      .. code-block:: bash

          poetry install
          poetry run lizard -C 10 examples/c_hello_world/src examples/c_hello_world/include

- **Rust**: `cargo-cyclo <https://github.com/fz0/cargo-cyclo>`_ (Cyclomatic Complexity)
   - Install once: ``cargo install cargo-cyclo``
   - Then run from within the Rust example:

      .. code-block:: bash

          cd examples/rust_hello_world
          cargo cyclo

The example scripts treat complexity reporting as **best-effort** by default (they do not fail
the workflow if the tool is not installed). For CI, you can tighten this to enforce thresholds.

Troubleshooting
===============

- PlantUML in offline environments: set ``PLANTUML_JAR`` or install PlantUML locally.
- Broken trace links: prefer ``:need:`ID``` references over plain-text IDs.
- ID validation failures: keep IDs uppercase with underscores (e.g., ``REQ_SAFETY_001``).
