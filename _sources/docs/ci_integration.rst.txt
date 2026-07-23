==================================
Integrating Verification into CI
==================================

Once ``osqar_project.json`` defines the verification plan and you have a working
``build-and-test.sh``, the next step is wiring everything into an automated CI
pipeline that produces auditable evidence on every commit.

This guide uses the `OSQAr-cJSON`_ project as the reference implementation — its
shell script + GitHub Actions workflow combination runs the full qualification
lifecycle on every push and produces a SHA256SUMS-manifested shipment on every
version tag.

.. _`OSQAr-cJSON`: https://github.com/BitVortex/OSQAr-cJSON

Architecture
============

The verification pipeline has three layers:

1. **Shell script** (``build-and-test.sh``) — the single entry point that runs the
   actual tools: compiler, test suite, sanitizers, lcov, lizard, cppcheck.  It
   accepts subcommands (``build``, ``test``, ``sanitizer``, ``coverage``,
   ``complexity``, ``static-analysis``, ``all``) so individual phases can be
   iterated on locally without running the full pipeline.

2. **CI workflow** (``.github/workflows/ci.yml``) — calls
   ``build-and-test.sh all``, builds Sphinx documentation, runs traceability
   checks, assembles the shipment, generates checksums, packages the ZIP, and
   creates a GitHub Release on tags.  Optionally deploys Sphinx HTML to GitHub
   Pages.

3. **OSQAr CLI** (``osqar traceability``, ``osqar checksum``, ``osqar
   shipment``) — invoked by CI for traceability verification, integrity
   manifests, and shipment packaging.

Use the `OSQAr-cJSON CI workflow`_ as a concrete reference. OSQAr does not ship a
generic CI workflow template: build commands, evidence producers, required tools,
and acceptance criteria are project-specific.

.. _`OSQAr-cJSON CI workflow`: https://github.com/BitVortex/OSQAr-cJSON/blob/main/.github/workflows/ci.yml

Step 1: Write ``build-and-test.sh``
===================================

The shell script is the heart of the pipeline.  It must:

- Use the qualified toolchain consistently (same compiler, flags, language standard).
- Compile the **actual library source** — not a demo or stub program.
- Run the real test suite and emit JUnit XML parsed from the test runner output.
- Run sanitizer-instrumented tests (ASan+UBSan) and capture their logs.
- Measure coverage with ``--coverage`` + ``lcov``, aggregating across **all**
  test binaries (see :ref:`ci-pitfalls-coverage` below).
- Run ``lizard`` for cyclomatic complexity analysis, capturing raw output.
- Run ``cppcheck`` for static analysis, capturing findings as XML.
- Run a compiler warning audit with ``-Werror`` and capture stderr.
- Accept subcommands so individual phases can be iterated on quickly.
- Exit non-zero on any failure (``set -euo pipefail``).

Reference: `OSQAr-cJSON build-and-test.sh`_ (covers the verification activities
selected for that ISO 26262 SEooC qualification attempt targeting ASIL D).

.. _`OSQAr-cJSON build-and-test.sh`: https://github.com/BitVortex/OSQAr-cJSON/blob/main/build-and-test.sh

Step 2: Wire the CI workflow
============================

Create ``.github/workflows/ci.yml`` for the project, using the reference workflow
as a starting point where appropriate. At minimum, adapt:

* the project identifier and source files included in the shipment;
* required system and Python tool dependencies;
* the pinned OSQAr version;
* verification and implementation need-ID prefixes;
* project-specific build, test, analyzer, and evidence-acceptance commands; and
* tag patterns, artifact retention, publication permissions, and protected
  environments.

The workflow triggers on pushes to ``main`` and on tags matching
``<libversion>-<osqarversion>`` (e.g., ``1.7.19-0.9.0``).

CI job summary
--------------

The ``qualify`` job runs these steps in order:

1. **Checkout** — source code plus submodules.
2. **Install tool dependencies** — ``apt`` packages, ``pip`` packages (lizard,
   coverage), Sphinx doc dependencies.
3. **Install OSQAr CLI** — pinned version via ``pip``.
4. **Build and test** — ``./build-and-test.sh all``, which produces
   ``test_results.xml``, ``coverage_report.txt``, ``complexity_report.txt``,
   and sanitizer/static-analysis evidence.
5. **Build Sphinx documentation** — ``sphinx-build -b html -W``, verifying that
   ``needs.json`` is produced.
6. **Upload Sphinx HTML artifact** — for later Pages deployment.
7. **Run OSQAr doctor** — diagnostic overview (non-fatal).
8. **Traceability check** — ``osqar traceability`` with custom prefix overrides.
9. **Assemble shipment** — copy documentation, source code, reports, and
   verification evidence into ``_shipment/``.
10. **Generate and verify checksums** — ``osqar checksum generate`` +
    ``osqar checksum verify``.
11. **Package shipment** — ``osqar shipment package`` → ZIP.
12. **Upload shipment artifact** — 90-day retention.
13. **Create GitHub Release** (on tag) — uploads the shipment ZIP and
    SHA256SUMS to the release page.

Step 3: Configure shipment assembly
====================================

The "Assemble shipment" step copies artifacts into a structured ``_shipment/``
directory:

.. code-block:: text

   _shipment/
   ├── docs/              # Sphinx HTML build
   ├── implementation/     # Source files, osqar_project.json, build-and-test.sh
   ├── tests/              # Test suite source (for reproducibility)
   ├── reports/            # test_results.xml, coverage_report.txt, complexity_report.txt
   ├── verification/       # Sanitizer logs, cppcheck XML, compiler warning audit
   └── SHA256SUMS          # Integrity manifest (generated by osqar checksum)

Every file is checksummed into ``SHA256SUMS``.  The shipment ZIP is the
auditable evidence package — it contains everything an auditor needs to
reproduce and verify the qualification.

Step 4: Verify the pipeline locally
====================================

Before pushing to CI, verify the full pipeline end-to-end:

.. code-block:: bash

   # Run the full verification pipeline
   ./build-and-test.sh all

   # All three evidence artifacts must exist and contain real data
   test -s test_results.xml || echo "MISSING: test_results.xml"
   test -s coverage_report.txt || echo "MISSING: coverage_report.txt"
   test -s complexity_report.txt || echo "MISSING: complexity_report.txt"

   # Build docs and run traceability
   python3 -m sphinx -b html -W . _build/html
   osqar traceability _build/html/needs.json \
       --test-prefix VER_ --code-prefix IMPL_

   # Assemble, checksum, and verify the shipment (simulates CI)
   osqar shipment prepare --project . --skip-verification
   osqar checksum generate --root _shipment --output _shipment/SHA256SUMS
   osqar checksum verify --root _shipment --manifest _shipment/SHA256SUMS

.. important::

   Every evidence artifact (``test_results.xml``, ``coverage_report.txt``,
   ``complexity_report.txt``) must contain **live measurement data** from actual
   tool runs.  Never use shell heredocs with hand-written numbers claiming fake
   coverage or test counts.  Verify each file was produced by parsing real tool
   output before committing the CI workflow.

Step 5: Create a version tag
=============================

When the pipeline passes, tag a release to trigger the automated shipment:

.. code-block:: bash

   git tag -a "1.7.19-0.9.0" -m "Library v1.7.19 — OSQAr v0.9.0 qualification"
   git push origin "1.7.19-0.9.0"

CI runs on the tag push, assembles the shipment, and creates a GitHub Release
with the shipment ZIP and SHA256SUMS attached.

Reference implementation
========================

`OSQAr-cJSON`_ is the canonical reference for a complete verification pipeline:

- **162 Unity tests** across 21 executables, zero failures
- **88.1% statement coverage** aggregated via ``lcov`` across all test binaries
- **Zero compiler warnings** with ``-Werror -Wall -Wextra -Wconversion``
- **ASan+UBSan clean** on the full test suite
- **Zero traceability violations** (custom prefixes: ``VER_``, ``IMPL_``)
- **SHA256SUMS-manifested shipment ZIP** on every ``1.7.19-X.Y.Z`` tag
- **GitHub Pages** with full Sphinx HTML documentation at
  `bitvortex.github.io/OSQAr-cJSON <https://bitvortex.github.io/OSQAr-cJSON/>`_

Key files to study:

- `ci.yml <https://github.com/BitVortex/OSQAr-cJSON/blob/main/.github/workflows/ci.yml>`_ — CI workflow
- `build-and-test.sh <https://github.com/BitVortex/OSQAr-cJSON/blob/main/build-and-test.sh>`_ — verification pipeline
- `osqar_project.json <https://github.com/BitVortex/OSQAr-cJSON/blob/main/osqar_project.json>`_ — project config with gap definitions
- `conf.py <https://github.com/BitVortex/OSQAr-cJSON/blob/main/conf.py>`_ — Sphinx config with PlantUML and custom need prefixes

.. _ci-pitfalls:

Common CI pitfalls
==================

PlantUML command vs server
   Setting ``plantuml = "https://..."`` in ``conf.py`` causes Sphinx to try to
   ``exec()`` the URL.  Use ``plantuml_server`` for web URLs.  The OSQAr
   ``conf.py`` template handles this automatically (see the PlantUML
   configuration in :doc:`cli_reference`).

lizard is pip-only
   The complexity analysis tool ``lizard`` is **not** available via ``apt`` on
   Ubuntu 24.04.  Install with ``pip install lizard`` in the CI workflow.  All
   other Python dependencies (Sphinx, sphinx-needs, sphinxcontrib-plantuml,
   furo, pyyaml) are pulled transitively by installing OSQAr itself.

PlantUML ``!theme`` on older CI runners
   Ubuntu's ``apt install plantuml`` ships v1.2020.2, which does not support
   ``!theme``.  Use ``skinparam`` directives instead to keep diagrams portable
   across local and CI environments.

.. _ci-pitfalls-coverage:

Coverage aggregation across test binaries
   When a library is statically linked into multiple test executables, each
   binary produces its own ``.gcda`` file.  Aggregate them with::

       lcov --capture -d build_dir -o coverage.info
       lcov -e coverage.info '*/your_lib.c' -o coverage_filtered.info

   Do **not** delete individual test binary ``.gcda`` files — they contain the
   library coverage counters.  ``gcovr`` path-resolution fails on multi-binary
   projects; prefer ``lcov``.

Evidence artifacts must be live measurements
   The most dangerous class of pipeline bugs is fabricated evidence: shell
   heredocs with hand-written numbers posing as tool output.  Always verify that
   ``test_results.xml``, ``coverage_report.txt``, and ``complexity_report.txt``
   are produced by actual tool runs, not static text blocks.

Pages deployment environment block
   Do **not** add an ``environment:`` block to the ``pages`` job in CI —
   ``actions/deploy-pages@v4`` handles environment creation internally.  Adding
   one causes the job to fail instantly with zero steps executed.

GitHub Pages setup (one-time)
=============================

To publish Sphinx HTML documentation via GitHub Pages on every tag:

.. code-block:: bash

   # Enable Pages on the repo
   gh api /repos/<owner>/<repo>/pages \
       -X POST -f 'source[branch]=main' -f 'source[path]=/docs'

   # Switch to workflow-based deployment
   gh api /repos/<owner>/<repo>/pages -X PUT -f 'build_type=workflow'

The CI template includes a ``pages`` job that depends on ``qualify``, downloads
the Sphinx HTML artifact, and deploys via ``actions/deploy-pages@v4``.
