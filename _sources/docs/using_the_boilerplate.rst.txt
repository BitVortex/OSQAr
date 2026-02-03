===========================
Using the OSQAr Boilerplate
===========================

Purpose
=======

OSQAr is a **documentation-first framework** for producing, verifying, and integrating **auditable evidence shipments** for safety/compliance work.

In OSQAr, an evidence shipment is the unit you transfer and archive: a bundle that contains **Sphinx documentation with maintained traceability**, plus the **implementation**, **tests**, and **analysis/verification reports** needed to review and audit the evidence end-to-end.

OSQAr provides:

- structured requirements and traceability (via ``sphinx-needs``)
- architecture diagrams (via PlantUML)
- verification planning and traceability (requirements ↔ architecture ↔ tests)
- evidence “shipments” (documentation + traceability + implementation + tests + analysis reports) protected by checksum manifests
- integrator-friendly multi-shipment intake and a consolidated **Subproject overview**
- extensive lifecycle management guidance (framework-level and example-level)

This chapter is the main entrypoint. It gives you the mental model and the first commands to run.

Recommended reading order
=========================

1. You are here: build docs, understand the workflow, and explore examples.
2. Set up and migrate a project: :doc:`project_setup_from_scratch`.
3. As a supplier, learn how to ship evidence bundles: :doc:`suppliers_guide`.
4. As an integrator, learn how to verify and archive shipments: :doc:`integrators_guide`.
5. If you work with many shipments, use: :doc:`multi_project_workflows`.
6. For release/baseline discipline, see: :doc:`lifecycle_management`.
7. For team-scale collaboration, see: :doc:`collaboration_workflows`.

Typical workflow
================

1. Author needs objects (REQ/ARCH/TEST) in RST with stable IDs.
2. Build HTML docs and export machine-readable artifacts (e.g. ``needs.json``).
3. Run traceability checks and store the report.
4. Generate a checksum manifest (e.g. ``SHA256SUMS``) for integrity.
5. Transfer/archive the shipment; integrators verify checksums and (optionally) re-run checks.

Quick start
===========

Install options
---------------

OSQAr keeps the default Python dependency footprint lean. Install additional tooling only if you need it:

- Core docs + CLI (recommended default)::

   poetry install

- Evidence tooling (coverage/complexity generation used by example scripts)::

   poetry install --with evidence

- IDE tooling (optional Sphinx language server for VS Code)::

   poetry install --with ide

Build the rendered HTML documentation from the repository root:

.. code-block:: bash

   poetry install
   poetry run sphinx-build -b html . _build/html
   open _build/html/index.html

Reproducible native builds (C / C++ / Rust)
===========================================

OSQAr’s documentation builds are already dependency-locked via Poetry.
For **native code** (C/C++/Rust), OSQAr also provides a small “reproducible build” mode in the examples.

The goals are:

- stable timestamps (via ``SOURCE_DATE_EPOCH``)
- stable embedded source paths (via compiler path remapping)
- reduced build-environment noise (UTC timezone + stable locale)

The example build scripts accept either the environment flag ``OSQAR_REPRODUCIBLE=1`` or the CLI flag ``--reproducible``.

.. code-block:: bash

   # Use the latest git commit timestamp as a stable build time
   export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"

   # C example
   cd examples/c_hello_world
   OSQAR_REPRODUCIBLE=1 ./build-and-test.sh

   # C++ example
   cd ../cpp_hello_world
   OSQAR_REPRODUCIBLE=1 ./build-and-test.sh

   # Rust example
   cd ../rust_hello_world
   OSQAR_REPRODUCIBLE=1 ./build-and-test.sh

Notes:

- The reproducible mode is implemented as a small helper script (vendored into each example at ``osqar_tools/reproducible_build_env.sh``) and is intentionally lightweight.
- The shipped *test report XML* in the examples does not include timestamps, so it is stable across runs.

Optional: Bazel integration
---------------------------

If you prefer Bazel for a more “CI-native” workflow, the C, C++, and Rust examples include minimal Bazel files.

Reproducible mode for Bazel is supported via the wrapper script in each example (it applies the same path remapping and stable environment as the non-Bazel scripts, and runs Bazel with ``--config=reproducible``).

.. code-block:: bash

   cd examples/c_hello_world
   # Non-reproducible (default)
   bazel build //...
   bazel run //:junit_tests -- test_results.xml

   # Reproducible
   export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
   OSQAR_REPRODUCIBLE=1 ./bazel-build-and-test.sh

   cd ../cpp_hello_world
   bazel build //...
   bazel run //:junit_tests -- test_results.xml

   export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
   OSQAR_REPRODUCIBLE=1 ./bazel-build-and-test.sh

   cd ../rust_hello_world
   bazel build //...
   bazel run //:junit_tests -- test_results.xml

   export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
   OSQAR_REPRODUCIBLE=1 ./bazel-build-and-test.sh

CI-built demo shipments (downloadable)
======================================

This repository’s CI builds **downloadable, integrity-protected example shipments** for the C, C++, and Rust examples.

Each example shipment contains:

- rendered HTML documentation (with maintained traceability)
- implementation sources and tests
- analysis/verification reports:

   - ``test_results.xml`` (JUnit)
   - ``coverage_report.txt`` (coverage summary; language-specific tooling)
   - ``complexity_report.txt`` (complexity summary)

- ``needs.json`` (trace graph export)
- ``traceability_report.json`` (OSQAr traceability validation output)
- ``SHA256SUMS`` (checksum manifest for the whole bundle directory)

CI exports deterministic archives (``.tar.gz``) for each example as well as a combined archive.
In GitHub Actions, download the artifact named ``osqar-example-shipments`` from the ``Tests and Example Shipments`` workflow run.

Reference examples
==================

OSQAr primarily targets **C**, **C++**, and **Rust** projects.

Each example produces:

- native test results as `test_results.xml` (JUnit)
- rendered HTML documentation; the examples can optionally import JUnit XML into the docs via `sphinx-test-reports`

Build any example documentation directly:

.. code-block:: bash

   poetry install
   poetry run sphinx-build -b html examples/c_hello_world _build/html/examples/c
   poetry run sphinx-build -b html examples/cpp_hello_world _build/html/examples/cpp
   poetry run sphinx-build -b html examples/rust_hello_world _build/html/examples/rust

Run an end-to-end workflow (native tests → docs) for an example:

.. code-block:: bash

   # Optional: install extra tooling to generate coverage/complexity evidence
   poetry install --with evidence

   cd examples/c_hello_world
   ./build-and-test.sh
   open _build/html/index.html

Python demo (workstation reference)
-----------------------------------

A Python example remains available as a documentation reference variant:

.. code-block:: bash

   # Optional: install extra tooling to generate coverage/complexity evidence
   poetry install --with evidence

   cd examples/python_hello_world
   ./build-and-test.sh
   open _build/html/index.html

OSQAr CLI
=========

OSQAr includes a small, stdlib-only CLI for common workflows:

- scaffold a new project from a language template
- validate traceability based on an exported ``needs.json``
- generate/verify checksum manifests for a shipped evidence bundle
- supplier and integrator workflows (prepare, verify, intake)
- optional shipment metadata (origin, URLs, descriptive info)

For guidance on large-team collaboration (branching, merging, conflict minimization), see
:doc:`collaboration_workflows`.

Invocation
----------

Run via Poetry:

.. code-block:: bash

   poetry run python -m tools.osqar_cli --help

Or via the repo-root convenience wrapper:

.. code-block:: bash

   ./osqar --help

Scaffold a new project
----------------------

Create a new project folder based on one of the reference templates:

For a step-by-step guide (including how to migrate existing sources and documentation, and how to ship a release with OSQAr evidence), see :doc:`project_setup_from_scratch`.

.. code-block:: bash

   poetry run python -m tools.osqar_cli new --language c --name MySEooC --destination ./MySEooC

This copies the selected template while excluding build outputs (e.g., ``_build/``, ``target/``, ``__pycache__/``).

Verify traceability
-------------------

Run traceability checks on an exported ``needs.json``:

.. code-block:: bash

   poetry run python -m tools.osqar_cli traceability ./_build/html/needs.json \
     --json-report ./_build/html/traceability_report.json

Checksum manifest (shipment integrity)
--------------------------------------

Generate and verify a checksum manifest (default: SHA-256) for a shipped directory:

.. code-block:: bash

   poetry run python -m tools.osqar_cli checksum generate --root ./_build/html --output ./_build/html/SHA256SUMS
   poetry run python -m tools.osqar_cli checksum verify --root ./_build/html --manifest ./_build/html/SHA256SUMS

Core authoring workflow
=======================

OSQAr works best when you keep a consistent structure:

- define requirements and constraints as ``.. need::`` objects with stable IDs
- link requirements ↔ architecture ↔ tests using ``:links:`` and ``:need:`ID``` references
- keep architecture diagrams in PlantUML sources under version control
- define verification requirements (``TEST_*``) and include traceability tables/matrices (e.g. via ``sphinx-needs`` directives)

Writing requirements (sphinx-needs)
-----------------------------------

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
---------------------

The boilerplate enforces ID discipline via ``needs_id_regex``.

A practical scheme is:

- ``REQ_SAFETY_*``: safety goals and safety requirements
- ``REQ_FUNC_*``: functional requirements
- ``ARCH_*``: architecture/design constraints and interfaces
- ``TEST_*``: verification requirements / test specifications

Architecture diagrams (PlantUML)
--------------------------------

PlantUML sources live in ``diagrams/`` and are included from RST:

.. code-block:: rst

   .. uml:: diagrams/02_data_flow.puml
      :caption: Data flow (budget: :need:`REQ_SAFETY_002`) — Architecture: :need:`ARCH_FUNC_001`, :need:`ARCH_FUNC_002`, :need:`ARCH_FUNC_003`

Verification and traceability
-----------------------------

A robust verification chapter typically contains:

1) test requirements as needs objects (``TEST_*``)
2) a traceability matrix mapping ``REQ_*``/``ARCH_*`` → ``TEST_*``

Shipment verification (per example output)
==========================================

OSQAr treats each **example build output directory** as a shippable evidence bundle.
This is the unit that is transferred, archived, and later verified (similar to a software shipment).

Per shipped example output directory, OSQAr expects the following files to be present:

- ``needs.json`` (export from ``sphinx-needs``)
- ``traceability_report.json`` (result of the OSQAr traceability check)
- ``SHA256SUMS`` (checksum manifest covering the full directory contents)
- ``osqar_project.json`` (optional project metadata: description, URLs, origin)

Supplier-side procedure (create the shipment)
---------------------------------------------

Build the example documentation so that ``needs.json`` is exported::

    poetry run sphinx-build -b html examples/python_hello_world examples/python_hello_world/_build/html

Run the traceability check (writes a machine-readable report)::

    poetry run python tools/traceability_check.py \
       examples/python_hello_world/_build/html/needs.json \
       --json-report examples/python_hello_world/_build/html/traceability_report.json

Generate and verify checksums for the example build output directory::

    poetry run python tools/generate_checksums.py \
       --root examples/python_hello_world/_build/html \
       --output examples/python_hello_world/_build/html/SHA256SUMS

    poetry run python tools/generate_checksums.py \
       --root examples/python_hello_world/_build/html \
       --verify examples/python_hello_world/_build/html/SHA256SUMS

Optional convenience (same operations via the OSQAr CLI)::

    # Supplier: build a shippable evidence directory in one command
    poetry run python -m tools.osqar_cli supplier prepare \
       --project examples/python_hello_world \
       --clean \
       --archive

    # Integrator: verify a received shipment (checksums + traceability)
    poetry run python -m tools.osqar_cli integrator verify \
       --shipment /path/to/shipment \
       --traceability

    # Supplier: optionally add metadata into the shipment root
    ./osqar shipment metadata write \
       --shipment examples/python_hello_world/_build/html \
       --name "OSQAr Python Hello World" \
       --version "0.3.0" \
       --url repository=https://example.com/repo.git \
       --origin url=https://example.com/repo.git \
       --origin revision=<commit>

    # Integrator: intake multiple shipments and generate a Subproject overview
    ./osqar workspace intake \
       --root intake/received \
       --recursive \
       --output intake/archive/2026-02-01 \
       --traceability

    # Or run the individual shipment steps
    poetry run python -m tools.osqar_cli shipment build-docs --project examples/python_hello_world
    poetry run python -m tools.osqar_cli shipment traceability --shipment examples/python_hello_world/_build/html
    poetry run python -m tools.osqar_cli shipment checksums --shipment examples/python_hello_world/_build/html generate
    poetry run python -m tools.osqar_cli shipment checksums --shipment examples/python_hello_world/_build/html verify

Then archive and ship the **example output directory** (not the framework docs built from the repo root).

For multi-project intake patterns, see :doc:`multi_project_workflows`.

Integrator-side procedure (verify a received shipment)
------------------------------------------------------

Verify the received directory against the provided manifest::

    poetry run python tools/generate_checksums.py \
       --root /path/to/shipment \
       --verify /path/to/shipment/SHA256SUMS

Optionally re-run the traceability checks on the shipped ``needs.json``::

    poetry run python tools/traceability_check.py \
       /path/to/shipment/needs.json \
       --json-report /path/to/shipment/traceability_report.integrator.json

For role-specific guidance (including what to do on mismatches), see:

- :doc:`suppliers_guide`
- :doc:`integrators_guide`

We also recommend getting familiar with suggestions on overall lifecycle management: 

- :doc:`lifecycle_management`

Code complexity (optional)
==========================

OSQAr supports generating additional *engineering evidence* artifacts alongside test results.

All reference examples include an optional **code complexity report** step that produces
``complexity_report.txt``.

- **C / C++ / Python**: `lizard <https://github.com/terryyin/lizard>`_ (Cyclomatic Complexity)
   - Runs as part of the example scripts via ``poetry run lizard``.
   - You can run it manually from the repository root, e.g.:

      .. code-block:: bash

          poetry install --with evidence
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
