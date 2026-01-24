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

Reference example
=================

To view the full reference example locally:

.. code-block:: bash

   poetry install
   poetry run sphinx-build -b html examples/hello_world examples/hello_world/_build/html/example
   open examples/hello_world/_build/html/example/index.html

Or run the example’s end-to-end workflow script (tests → docs):

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

Troubleshooting
===============

- PlantUML in offline environments: set ``PLANTUML_JAR`` or install PlantUML locally.
- Broken trace links: prefer ``:need:`ID``` references over plain-text IDs.
- ID validation failures: keep IDs uppercase with underscores (e.g., ``REQ_SAFETY_001``).
