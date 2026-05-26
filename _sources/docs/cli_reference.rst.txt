=============
CLI Reference
=============

This page is a **command reference** for the OSQAr CLI.

For workflow guidance and copy/paste recipes, see :doc:`using_the_boilerplate` (especially :ref:`quick-start` and :ref:`workflow-recipes`).


How To Use This Reference
=========================

1. Start with :ref:`cli-terms` (project vs shipment vs workspace).
2. Skim :ref:`cli-command-index` to find the right command.
3. Use the per-command sections for **Synopsis**, **Options**, and **Examples**.
4. When in doubt, run ``osqar <command> --help`` for the authoritative help text.


Invocation
==========

Preferred (installed CLI via pipx)
------------------------------------

.. code-block:: console

  pipx install osqar
  osqar --help

Repo-root wrappers (contributors / git checkout)
------------------------------------------------

.. code-block:: console

  ./osqar --help

Windows wrappers also exist in the repo root:

- ``.\osqar.cmd --help``
- ``.\osqar.ps1 --help``


.. _cli-terms:

Terminology
===========

Project (shipment project)
--------------------------

Directory that contains at least:

- ``conf.py``
- ``index.rst``

Examples live under ``examples/``.

Shipment directory (built evidence output)
------------------------------------------

The built HTML output directory, usually:

- ``<project>/_build/html``

This directory may contain artifacts such as ``index.html``, ``needs.json``, ``SHA256SUMS``, and reports.

Workspace (integrator side)
---------------------------

A directory that contains **multiple received shipments**. Workspace commands typically discover shipments
by scanning for ``SHA256SUMS`` in subdirectories.


Defaults and Conventions
========================

Default paths
-------------

- If a command takes ``--project`` and you omit it, the default is usually ``.``.
- If a command builds docs and you omit output, the default is usually ``<project>/_build/html``.

Exit codes
----------

As a rule of thumb:

- ``0``: success
- ``1``: verification/checks failed (but the command ran)
- ``2``: invalid usage or required input missing
- ``127``: an external tool command was not found (only for hooks/custom commands)

Machine-readable reports
------------------------

Some commands can write JSON reports for CI and audit trails:

- ``doctor --json-report`` writes ``schema: osqar.doctor_report.v1``
- ``traceability --json-report`` writes ``schema: osqar.traceability_report.v1``
- ``impact --format json`` writes ``schema: osqar.impact_report.v1``
- ``baseline diff --format json`` writes ``schema: osqar.baseline_diff.v1``
- ``checksum ... --json-report`` writes ``schema: osqar.checksums_report.v1``
- ``code-trace --json-report`` writes ``schema: osqar.code_trace_report.v1``
- ``shipment verify --report-json`` writes ``schema: osqar.shipment_verify_report.v1``


Configuration and Hooks
=======================

OSQAr supports optional JSON config files to customize commands and run hooks around events.
For the full configuration schema and examples, see :doc:`configuration_and_hooks`.

Two config files are relevant:

- Project config: ``osqar_project.json`` (supplier/dev side; stored in the **project root**)
- Workspace config: ``osqar_workspace.json`` (integrator side; stored in a **trusted workspace root**)

Security note (important)
-------------------------

Treat configuration files inside received bundles as **untrusted input**.
Only use workspace config from a location you control.

Common flags and environment
----------------------------

- ``--config <path>`` overrides the config path (project/workspace depending on the command).
- ``--no-hooks`` disables running hooks for this invocation.
- ``OSQAR_DISABLE_HOOKS=1`` disables hooks globally.

Execution model
---------------

Configured hook/command strings are split into argv (Python ``shlex``) and executed **without a shell**.

If you need shell features (pipes, ``&&``, redirects), wrap explicitly, for example:

.. code-block:: console

  bash -lc 'set -euo pipefail; make test && make docs'

Common hook events
------------------

Hook event names are simple strings. Current events include:

- ``shipment.prepare``, ``shipment.build-docs``, ``shipment.run-tests``, ``shipment.run-build``
- ``shipment.verify``
- ``workspace.report``, ``workspace.verify``, ``workspace.verify.shipment``, ``workspace.intake``

Environment variables set by OSQAr
----------------------------------

Some commands provide context for hooks via environment variables:

- ``OSQAR_PROJECT_DIR``: absolute project directory
- ``OSQAR_DOCS_OUTPUT``: absolute docs output directory


.. _cli-command-index:

Command Index
=============

Top-level commands
------------------

- :ref:`cli-build-docs` — Build Sphinx HTML output (shortcut).
- :ref:`cli-open-docs` — Open built HTML documentation (``index.html``).
- :ref:`cli-setup` — Verify/extract a downloaded ZIP and run verification.
- :ref:`cli-doctor` — Environment + shipment diagnostics.
- :ref:`cli-impact` — Change impact analysis via traceability graph traversal.
- :ref:`cli-new` — Scaffold a new OSQAr project.
- :ref:`cli-traceability` — Validate traceability rules from ``needs.json`` (supports CSV and Excel export).
- :ref:`cli-code-trace` — Scan code for need IDs (optional enforcement).
- :ref:`cli-baseline` — Versioned requirement baselines (snapshot, list, diff).
- :ref:`cli-checksum` — Generate/verify checksum manifests.
- :ref:`cli-framework` — Framework bundle helpers (release/CI).
- :ref:`cli-gsn` — GSN safety case diagrams (PlantUML and gsn2x backends).
- :ref:`cli-shipment` — Shipment workflows (build, prepare, verify, package, incremental).
- :ref:`cli-sign` — Cryptographic manifest signing (GPG detached signatures).
- :ref:`cli-workspace` — Workspace workflows (list, report, diff, verify, intake, combine, traceability).


Top-Level Commands
==================


.. _cli-build-docs:

build-docs
----------

Build Sphinx HTML documentation for a shipment project.
This is a shortcut for ``osqar shipment build-docs``.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar build-docs [--project <dir>] [--config <path>] [--no-hooks]
            [--output <dir>] [--open]

Options
^^^^^^^

- ``--project``: shipment project directory (default: ``.``; must contain ``conf.py`` and ``index.rst``)
- ``--config``: project config JSON (default: ``<project>/osqar_project.json``)
- ``--no-hooks``: disable pre/post hooks (also disable via ``OSQAR_DISABLE_HOOKS=1``)
- ``--output``: output directory (default: ``<project>/_build/html``)
- ``--open``: open the built ``index.html`` in your default browser

Notes
^^^^^

If OSQAr detects a Poetry-managed project and ``poetry`` is available, it will build docs via
``poetry run python -m sphinx ...``.

Examples
^^^^^^^^

.. code-block:: console

  # Build docs for the current project
  osqar build-docs

  # Build docs for an example project
  osqar build-docs --project examples/c_hello_world

  # Build and open
  osqar build-docs --open


.. _cli-open-docs:

open-docs
---------

Open a built HTML documentation entrypoint (``index.html``) in your default browser.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar open-docs [--project <dir> | --shipment <dir> | --path <file-or-dir>] [--print-only]

Resolution rules
^^^^^^^^^^^^^^^^

- If ``--path`` is a directory, OSQAr opens ``<dir>/index.html``.
- If ``--shipment`` is provided, OSQAr opens ``<shipment>/index.html``.
- Otherwise OSQAr opens ``<project>/_build/html/index.html``.

Options
^^^^^^^

- ``--project``: project directory (default: ``.``)
- ``--shipment``: shipment directory
- ``--path``: explicit HTML file or directory
- ``--print-only``: print the resolved path instead of opening a browser

Examples
^^^^^^^^

.. code-block:: console

  # Open docs for the current project
  osqar open-docs

  # Open docs for a project
  osqar open-docs --project examples/python_hello_world

  # Open docs for a shipment directory
  osqar open-docs --shipment examples/python_hello_world/_build/html

  # Just show what would be opened
  osqar open-docs --print-only


.. _cli-setup:

setup
-----

Verify, extract, and then verify a downloaded shipment/workspace ZIP.

Intent
^^^^^^

- Make GitHub Release assets usable immediately (especially the combined example workspace).
- Verify a sibling checksum file (``.sha256`` / ``.sha256sum``) when present.

Behavior
^^^^^^^^

- If a checksum file is found next to the ZIP, OSQAr verifies it and fails on mismatch.
- If no checksum file is present, OSQAr emits a warning and continues.
- After extraction, OSQAr detects the bundle type and runs:

  - workspace bundle: ``osqar workspace verify --root .``
  - shipment bundle: ``osqar shipment verify --shipment .``

Synopsis
^^^^^^^^

.. code-block:: console

  osqar setup <zip> [--output <dir>] [--force]

Options
^^^^^^^

- ``zip``: path to a ``.zip`` archive
- ``--output``: extraction directory (default: ``<zip path without .zip>``)
- ``--force``: overwrite the output directory if it exists

Example
^^^^^^^

.. code-block:: console

  osqar setup osqar_example_workspace_<tag>.zip


.. _cli-doctor:

doctor
------

Run a best-effort diagnostics report.

What it checks
^^^^^^^^^^^^^^

- Environment diagnostics (unless ``--skip-env-checks``)
  - Poetry availability (if the project is Poetry-managed)
  - Sphinx importability (in the environment used by ``build-docs``)
  - PlantUML availability (``plantuml`` command, or ``PLANTUML_JAR`` + ``java``)
- Shipment diagnostics (unless ``--skip-shipment-checks``)
  - presence of common artifacts (``index.html``, ``needs.json``, ``SHA256SUMS``, metadata)
  - optional checksum verify and optional traceability check

Synopsis
^^^^^^^^

.. code-block:: console

  osqar doctor [--project <dir>] [--shipment <dir>] [--json-report <path>]
          [--traceability] [--needs-json <path>] [--exclude <glob> ...]
          [--skip-checksums] [--skip-traceability]
          [--skip-shipment-checks] [--skip-env-checks]
          [--enforce-req-has-test] [--enforce-arch-traces-req] [--enforce-test-traces-req]
          [--req-prefix <prefix> ...] [--arch-prefix <prefix> ...]
          [--test-prefix <prefix> ...] [--code-prefix <prefix> ...]

Options
^^^^^^^

- ``--project``: project directory (default: ``.``)
- ``--shipment``: shipment directory (default: ``<project>/_build/html`` if present)
- ``--json-report``: write a machine-readable JSON report
- ``--traceability``: also run traceability checks if ``needs.json`` is available
- ``--needs-json``: override needs.json path for ``--traceability``
- ``--exclude``: exclude glob(s) for checksum verification (repeatable)
- ``--skip-checksums``: skip checksum verification even if ``SHA256SUMS`` exists
- ``--skip-traceability``: skip traceability checks even if ``needs.json`` exists
- ``--skip-shipment-checks``: skip shipment artifact checks
- ``--skip-env-checks``: skip environment checks (useful for diagnosing received shipments)

Examples
^^^^^^^^

.. code-block:: console

  # Before shipping: check environment + built artifacts (if present)
  osqar doctor

  # Diagnose a received shipment directory without requiring build tools
  osqar doctor --shipment /path/to/shipment --skip-env-checks --json-report doctor_report.json


.. _cli-impact:

impact
------

Analyze change impact by traversing traceability links from a seed need ID.

This command answers *"if I change this requirement, what else is affected?"* — supporting
ISO 26262-8 §9.4.2.4 impact analysis workflows. It performs bidirectional graph traversal
on the ``needs.json`` traceability graph and shows all reachable needs with their type,
status, and title.

See :doc:`lifecycle_management` for integrating impact analysis into your change control process.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar impact <needs_json> --need-id <id>
         [--direction {downstream,upstream,both}] [--max-depth <n>]
         [--format {tree,json}] [--json-report <path>]

Options
^^^^^^^

- ``needs_json``: path to ``needs.json`` produced by sphinx-needs
- ``--need-id``: required; seed need ID to start traversal from
- ``--direction``: traversal direction (default: ``both``)
- ``--max-depth``: maximum traversal depth (0 = unlimited; default: 0)
- ``--format``: output format (default: ``tree``; ``json`` for machine-readable)
- ``--json-report``: write JSON report to this path (only with ``--format json``)

Output formats
^^^^^^^^^^^^^^

**Tree** (default) — renders an ASCII tree showing each affected need with its type,
status, and title. The tree follows parent-child relationships derived from
traceability link depth:

.. code-block:: text

  REQ_CJSON_ARITH_SAFE (requirement)
  └── REQ_CJSON_ARITH_SAFE (requirement, active) — All integer arithmetic...
      ├── ARCH_PRINTER_FLOW (architecture, active) — The cJSON printer...
      │   └── REQ_CJSON_PRINT_VALID (requirement, active) — The cJSON printer...
      │       └── VER_CJSON_TEST_SUITE (verification, active) — Execute the full...
      ├── VER_CJSON_ARITH (verification, active) — Audit integer operations...
      └── VER_CJSON_STATIC (verification, active) — Run static analysis...

  Summary: 35 affected needs (7 architectures, 3 implementations, 11 requirements, 13 verifications)

**JSON** — structured report with ``affected_total``, ``affected_by_type`` counts, and
a sorted ``needs`` array:

.. code-block:: json

  {
    "schema": "osqar.impact_report.v1",
    "seed": "REQ_CJSON_ARITH_SAFE",
    "affected_total": 35,
    "affected_by_type": {
      "architecture": 7,
      "implementation": 3,
      "requirement": 11,
      "verification": 13
    }
  }

Examples
^^^^^^^^

.. code-block:: console

  # Show what would be affected if a requirement changes
  osqar impact ./_build/html/needs.json --need-id REQ_CJSON_PARSE_VALID

  # Downstream-only (what does this requirement feed into?)
  osqar impact ./_build/html/needs.json --need-id REQ_CJSON_MEMORY_SAFE --direction downstream

  # Machine-readable for CI
  osqar impact ./_build/html/needs.json --need-id REQ_CJSON_ARITH_SAFE --format json --json-report impact_report.json


.. _cli-new:

new
---

Create a new OSQAr project from a language template.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar new --language {c,cpp,python,rust} --name <name>
        [--destination <dir>] [--template {basic,example}] [--force]
        [--fallback-basic] [--no-diagrams]

Options
^^^^^^^

- ``--language``: required; one of ``c``, ``cpp``, ``python``, ``rust``
- ``--name``: required; project name
- ``--destination``: destination directory (default: ``./<name>``)
- ``--template``: template profile (default: ``basic``)

  - ``basic`` uses packaged templates
  - ``example`` copies from the repo examples (not available in the PyPI distribution)

- ``--force``: overwrite destination if it exists
- ``--fallback-basic``: silently fall back to ``--template basic`` when example templates are unavailable (e.g., from a PyPI install)
- ``--no-diagrams``: generate ``conf.py`` with PlantUML disabled (no diagram dependencies)

Example
^^^^^^^

.. code-block:: console

  osqar new --language c --name MySEooC --destination ../MySEooC


.. _cli-traceability:

traceability
------------

Run traceability checks on a ``needs.json`` export (from sphinx-needs), or
export a traceability matrix as CSV or Excel (XLSX) for auditor review.

Synopsis
^^^^^^^^

.. code-block:: console

  # Violation check (default)
  osqar traceability <needs_json> [--json-report <path>]
              [--enforce-req-has-test] [--enforce-arch-traces-req] [--enforce-test-traces-req]
              [--req-prefix <prefix> ...] [--arch-prefix <prefix> ...]
              [--test-prefix <prefix> ...] [--code-prefix <prefix> ...]

  # CSV export
  osqar traceability <needs_json> --format csv --format-output <path>
              [--req-prefix <prefix> ...] [--test-prefix <prefix> ...]
              [--arch-prefix <prefix> ...] [--code-prefix <prefix> ...]
              [--lm-prefix <prefix> ...]

  # Excel (XLSX) export
  osqar traceability <needs_json> --format xlsx --format-output <path>
              [--req-prefix <prefix> ...] [--test-prefix <prefix> ...]
              [--arch-prefix <prefix> ...] [--code-prefix <prefix> ...]
              [--lm-prefix <prefix> ...]

Options
^^^^^^^

- ``needs_json``: path to ``needs.json``
- ``--json-report``: write a JSON report
- ``--format``: output mode — ``check`` (default) for violation checking, ``csv`` for traceability matrix export, ``xlsx`` for Excel spreadsheet export
- ``--format-output``: file path for CSV/XLSX export (required with ``--format csv`` or ``--format xlsx``)
- ``--lm-prefix``: lifecycle management ID prefix for CSV columns (repeatable; default: ``LM_``)
- ``--enforce-req-has-test``: fail if any ``REQ_*`` has no linked ``TEST_*``
- ``--enforce-arch-traces-req``: fail if any ``ARCH_*`` has no linked ``REQ_*``
- ``--enforce-test-traces-req``: fail if any ``TEST_*`` has no linked ``REQ_*``

Prefix overrides apply to both check and CSV modes:
``--req-prefix``, ``--arch-prefix``, ``--test-prefix``, ``--code-prefix`` (all repeatable).

CSV export format
^^^^^^^^^^^^^^^^^

When ``--format csv`` is used, the tool writes a spreadsheet-ready CSV with these
columns per requirement:

- ``REQ_ID`` — requirement identifier
- ``REQ_Title`` — human-readable title/description
- ``Status`` — need status (e.g., ``active``, ``draft``)
- ``Tags`` — semicolon-delimited need tags
- ``ARCH_Linked`` — semicolon-delimited architecture IDs
- ``VER_Linked`` — semicolon-delimited verification IDs
- ``IMPL_Linked`` — semicolon-delimited implementation IDs
- ``LM_Linked`` — semicolon-delimited lifecycle management IDs
- ``Other_Linked`` — any other linked IDs not matching the above prefixes
- ``Total_Links`` — total number of outgoing links

The CSV can be opened directly in Excel, Google Sheets, or LibreOffice Calc.

XLSX export format
^^^^^^^^^^^^^^^^^^

When ``--format xlsx`` is used, the tool writes a native Excel ``.xlsx`` spreadsheet
with the same columns and schema as the CSV export (see above). The XLSX file
includes bold headers and auto-fitted column widths. Requires ``openpyxl`` to be
installed (``pip install openpyxl``); the command prints a clear error if it is
missing.

Examples
^^^^^^^^

.. code-block:: console

  # Standard traceability check
  osqar traceability ./_build/html/needs.json --json-report ./_build/html/traceability_report.json

  # Export traceability matrix for auditors (CSV)
  osqar traceability ./_build/html/needs.json --format csv --format-output traceability_matrix.csv

  # Export as native Excel spreadsheet
  osqar traceability ./_build/html/needs.json --format xlsx --format-output traceability_matrix.xlsx

  # Export with custom test prefix
  osqar traceability ./_build/html/needs.json --format csv --format-output matrix.csv \\
    --test-prefix VER_ --code-prefix IMPL_


.. _cli-code-trace:

code-trace
----------

Scan implementation and test sources for need IDs embedded in text (commonly comments).

Typical uses
^^^^^^^^^^^^

- Reporting: show which files mention which IDs.
- Enforcement: ensure IDs defined in ``needs.json`` are referenced in code/tests.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar code-trace [--root <dir>] [--needs-json <path>] [--json-report <path>]
             [--impl-dir <path> ...] [--test-dir <path> ...]
             [--exclude <glob> ...] [--ext <.ext> ...] [--max-bytes <n>]
             [--enforce-req-in-impl] [--enforce-arch-in-impl]
             [--enforce-test-in-tests] [--enforce-no-unknown-ids]

Options
^^^^^^^

- ``--root``: project root to scan (default: ``.``)
- ``--needs-json``: optional; defines the expected ``REQ_/ARCH_/TEST_`` IDs
- ``--json-report``: write a machine-readable JSON report
- ``--impl-dir``: implementation directory/file relative to ``--root`` (repeatable; default: auto-detect)
- ``--test-dir``: test directory/file relative to ``--root`` (repeatable; default: auto-detect)
- ``--exclude``: exclude glob(s) relative to ``--root`` (repeatable)
- ``--ext``: file extension(s) to scan, including leading dot (repeatable)
- ``--max-bytes``: skip files larger than this many bytes

Enforcement options
^^^^^^^^^^^^^^^^^^^

These only make sense when ``--needs-json`` is provided:

- ``--enforce-req-in-impl``: fail if any ``REQ_*`` from needs.json is not found in implementation sources
- ``--enforce-arch-in-impl``: fail if any ``ARCH_*`` from needs.json is not found in implementation sources
- ``--enforce-test-in-tests``: fail if any ``TEST_*`` from needs.json is not found in test sources
- ``--enforce-no-unknown-ids``: fail if code mentions IDs not present in needs.json

Examples
^^^^^^^^

.. code-block:: console

  # Generate a report
  osqar code-trace --root . --needs-json ./_build/html/needs.json --json-report ./_build/html/code_trace_report.json

  # Enforce REQ/ARCH appear in implementation, TEST appear in tests
  osqar code-trace --root . --needs-json ./_build/html/needs.json \
    --enforce-req-in-impl --enforce-arch-in-impl --enforce-test-in-tests



.. _cli-checksum:

checksum
--------

Generate or verify checksum manifests for a directory.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar checksum generate --root <dir> --output <manifest>
                 [--exclude <glob> ...] [--json-report <path>]

  osqar checksum verify --root <dir> --manifest <manifest>
                [--exclude <glob> ...] [--json-report <path>]

Options (both subcommands)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- ``--root``: directory to hash / verify
- ``--exclude``: exclude glob(s) (repeatable)
- ``--json-report``: write a machine-readable JSON report (schema: ``osqar.checksums_report.v1``)

Subcommand-specific
^^^^^^^^^^^^^^^^^^^

- ``generate --output``: path of the manifest file to create
- ``verify --manifest``: path of the manifest file to verify against

Example
^^^^^^^

.. code-block:: console

  osqar checksum generate --root ./_build/html --output ./_build/html/SHA256SUMS


.. _cli-framework:

framework
---------

Framework bundle operations (used for CI/release packaging).

Subcommand: bundle
^^^^^^^^^^^^^^^^^^

Synopsis
^^^^^^^^

.. code-block:: console

  osqar framework bundle --version <tag>
                 [--docs-dir <dir>] [--output-dir <dir>]

Options
^^^^^^^

- ``--version``: required; release/tag version, e.g. ``v0.9.0``
- ``--docs-dir``: path to built framework HTML docs (default: ``_build/html``)
- ``--output-dir``: staging/output directory (default: ``_dist``)


.. _cli-shipment:

shipment
--------

The ``shipment`` command group contains operations that act on a project directory or a built shipment directory.

Subcommands
^^^^^^^^^^^

- ``shipment list`` — discover shipment projects under a directory
- ``shipment build-docs`` — build HTML docs for a project
- ``shipment prepare`` — build + verify + package workflow
- ``shipment verify`` — verify a received shipment directory
- ``shipment run-tests`` — run test/build script or configured command
- ``shipment run-build`` — run a project-specific build command
- ``shipment clean`` — remove generated outputs
- ``shipment traceability`` — traceability checks for a shipment directory
- ``shipment checksums`` — generate/verify checksums for a shipment directory
- ``shipment pin`` — compute a dependency pin from a shipment manifest
- ``shipment copy-test-reports`` — copy raw JUnit XML into a shipment directory
- ``shipment package`` — archive a shipment directory into a ``.zip``
- ``shipment metadata write`` — write ``osqar_project.json`` into a shipment directory


shipment prepare
^^^^^^^^^^^^^^^^

Build docs, run checks, and optionally create an archive.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar shipment prepare --project <dir>
     [--config <path>] [--no-hooks]
     [--shipment <dir>] [--clean] [--dry-run]
     [--script <name>] [--reproducible | --no-reproducible]
     [--skip-build] [--build-command <cmd>]
     [--skip-tests] [--test-command <cmd>]
     [--incremental] [--force]
     [--skip-verification]
     [--exclude <glob> ...]
     [--enforce-req-has-test] [--enforce-arch-traces-req] [--enforce-test-traces-req]
     [--req-prefix <prefix> ...] [--arch-prefix <prefix> ...]
     [--test-prefix <prefix> ...] [--code-prefix <prefix> ...]
     [--archive] [--archive-output <path>]
     [--doctor]
     [--skip-code-trace] [--code-trace-warn-only] [--enforce-no-unknown-ids]

Key options
^^^^^^^^^^^

- ``--project``: required; shipment project directory
- ``--shipment``: output shipment directory (default: ``<project>/_build/html``)
- ``--reproducible`` / ``--no-reproducible``: toggle reproducible mode (default: enabled)
- ``--test-command`` / ``--build-command``: override commands from config
- ``--incremental``: only re-run stages (build, test, verification, docs, code-trace,
  traceability) whose inputs have changed since the last successful run. Cache stored
  in ``<project>/.osqar-cache/stages.json``.
- ``--force``: with ``--incremental``, clear the cache and run all stages regardless.
- ``--archive``: also create a zip archive of the shipment directory
- ``--doctor``: write a doctor report into the shipped directory before generating checksums

Examples
^^^^^^^^

.. code-block:: console

  # Prepare a shippable bundle for a project
  osqar shipment prepare --project examples/python_hello_world

  # Prepare, create archive, and keep going even if code-trace warns
  osqar shipment prepare --project examples/python_hello_world --archive --code-trace-warn-only


shipment verify
^^^^^^^^^^^^^^^

Verify a received shipment directory (integrity plus optional traceability re-check).

Synopsis
^^^^^^^^

.. code-block:: console

  osqar shipment verify --shipment <dir>
     [--config-root <dir>] [--config <path>] [--no-hooks]
     [--verify-command <cmd> ...]
     [--manifest <path>] [--exclude <glob> ...]
     [--traceability] [--needs-json <path>] [--json-report <path>]
     [--report-json <path>] [--strict]
     [--skip-code-trace] [--code-trace-warn-only]
     [--enforce-no-unknown-ids]
     [--enforce-req-has-test] [--enforce-arch-traces-req] [--enforce-test-traces-req]
     [--req-prefix <prefix> ...] [--arch-prefix <prefix> ...]
     [--test-prefix <prefix> ...] [--code-prefix <prefix> ...]

Notes
^^^^^

- ``--config`` here refers to **workspace** config (integrator side).
- Use ``--verify-command`` to run additional integrator-side checks after built-in checks.


shipment list
^^^^^^^^^^^^^

Discover shipment projects (directories containing ``conf.py`` and ``index.rst``).

Synopsis
^^^^^^^^

.. code-block:: console

  osqar shipment list [--root <dir>] [--recursive] [--format {pretty,paths}]


shipment build-docs
^^^^^^^^^^^^^^^^^^^

Same as :ref:`cli-build-docs`, but namespaced.

.. code-block:: console

  osqar shipment build-docs [--project <dir>] [--config <path>] [--no-hooks] [--output <dir>] [--open]


shipment run-tests
^^^^^^^^^^^^^^^^^^

Run a shipment’s build/test step.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar shipment run-tests --project <dir>
     [--config <path>] [--no-hooks]
     [--command <cmd>] [--script <name>]
     [--reproducible]


shipment run-build
^^^^^^^^^^^^^^^^^^

Run a project-specific build command (usually configured via ``commands.build`` in ``osqar_project.json``).

Synopsis
^^^^^^^^

.. code-block:: console

  osqar shipment run-build --project <dir>
     [--config <path>] [--no-hooks]
     [--command <cmd>]
     [--reproducible]


shipment clean
^^^^^^^^^^^^^^

Remove generated outputs (conservative by default).

Synopsis
^^^^^^^^

.. code-block:: console

  osqar shipment clean --project <dir> [--dry-run] [--aggressive]


shipment traceability
^^^^^^^^^^^^^^^^^^^^^

Run traceability checks for a built shipment directory.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar shipment traceability --shipment <dir>
     [--needs-json <path>] [--json-report <path>]
     [--enforce-req-has-test] [--enforce-arch-traces-req] [--enforce-test-traces-req]
     [--req-prefix <prefix> ...] [--arch-prefix <prefix> ...]
     [--test-prefix <prefix> ...] [--code-prefix <prefix> ...]


shipment checksums
^^^^^^^^^^^^^^^^^^

Generate or verify checksum manifests for a shipment directory.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar shipment checksums --shipment <dir> [--manifest <path>] [--exclude <glob> ...]
                  [--json-report <path>] {generate,verify}


shipment pin
^^^^^^^^^^^^

Compute a stable pin from a shipment manifest (default: ``SHA256SUMS``).

This prints a hex SHA-256 digest of the manifest file bytes. It can be used to
identify an OSQAr-qualified dependency precisely.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar shipment pin --shipment <dir> [--manifest <path>] [--json-report <path>]


shipment copy-test-reports
^^^^^^^^^^^^^^^^^^^^^^^^^^

Copy raw JUnit XML test reports into a shipment directory.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar shipment copy-test-reports --project <dir> [--shipment <dir>]
                        [--glob <pattern> ...] [--dry-run]


shipment package
^^^^^^^^^^^^^^^^

Archive a shipment directory into a ``.zip``.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar shipment package --shipment <dir> [--output <path>] [--dry-run]


shipment metadata write
^^^^^^^^^^^^^^^^^^^^^^^

Write ``osqar_project.json`` into a shipment directory.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar shipment metadata write --shipment <dir>
     [--name <text>] [--id <stable-id>] [--version <ver>] [--description <text>]
     [--url KEY=VALUE ...] [--origin KEY=VALUE ...] [--set KEY=VALUE ...]
     [--overwrite] [--dry-run]


.. _cli-workspace:

workspace
---------

The ``workspace`` command group operates on multiple shipments in an integrator workspace.

If supplier-provided shipment metadata declares OSQAr-qualified dependencies, you can use
``--enforce-deps`` on workspace commands to fail on missing/ambiguous/conflicting dependencies.

Workspace commands that produce an output directory (e.g., ``workspace report`` / ``workspace intake``)
also write a machine-readable ``subproject_overview.json`` which includes ``dependency_analysis``
(summary counts, dependency resolutions, and any detected issues).

Subcommands
^^^^^^^^^^^

- ``workspace list`` — list discovered shipments (scan for ``SHA256SUMS``)
- ``workspace report`` — generate a workspace overview (JSON + HTML)
- ``workspace diff`` — diff two workspace reports
- ``workspace verify`` — verify many shipments
- ``workspace intake`` — verify and archive many shipments into a single intake directory
- ``workspace combine`` — merge multiple project ``needs.json`` exports with namespace prefixes for cross-project traceability
- ``workspace traceability`` — run traceability checks on a combined workspace ``needs.json``


workspace list
^^^^^^^^^^^^^^

Synopsis
^^^^^^^^

.. code-block:: console

  osqar workspace list [--root <dir>] [--config <path>] [--recursive]
                [--format {table,paths,json}] [--json-report <path>]


workspace report
^^^^^^^^^^^^^^^^

Generate a subproject overview without copying shipments.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar workspace report [--root <dir>] [--config <path>] [--no-hooks] [--recursive]
                 --output <dir>
                 [--checksums] [--traceability] [--doctor]
                 [--needs-json <path>] [--exclude <glob> ...]
                 [--enforce-deps]
                 [--enforce-req-has-test] [--enforce-arch-traces-req] [--enforce-test-traces-req]
                 [--continue-on-error] [--json-report <path>] [--open]

Examples
^^^^^^^^

.. code-block:: console

  # List shipments under a folder
  osqar workspace list --root intake/received --recursive

  # Generate an overview without copying
  osqar workspace report --root intake/received --recursive --output intake/overview

  # Overview + verify checksums + traceability
  osqar workspace report --root intake/received --recursive --output intake/overview --checksums --traceability

  # Open the rendered HTML overview
  osqar workspace report --root intake/received --recursive --output intake/overview --open


workspace diff
^^^^^^^^^^^^^^

Synopsis
^^^^^^^^

.. code-block:: console

  osqar workspace diff <old_report.json> <new_report.json>


workspace verify
^^^^^^^^^^^^^^^^

Verify many shipments (discover by scanning for ``SHA256SUMS``).

Synopsis
^^^^^^^^

.. code-block:: console

  osqar workspace verify [--root <dir>] [--config <path>] [--no-hooks]
                 [--verify-command <cmd> ...] [--recursive]
                 [--exclude <glob> ...]
                 [--traceability] [--doctor] [--needs-json <path>]
                 [--enforce-deps]
                 [--enforce-req-has-test] [--enforce-arch-traces-req] [--enforce-test-traces-req]
                 [--continue-on-error] [--json-report <path>]


workspace intake
^^^^^^^^^^^^^^^^

Verify and archive multiple shipments into a single intake directory.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar workspace intake [<shipment_dir> ...]
                 [--root <dir>] [--config <path>] [--no-hooks] [--recursive]
                 --output <dir> [--force] [--dry-run]
                 [--exclude <glob> ...]
                 [--traceability] [--doctor] [--needs-json <path>]
                 [--enforce-deps]
                 [--enforce-req-has-test] [--enforce-arch-traces-req] [--enforce-test-traces-req]
                 [--continue-on-error]


.. _cli-baseline:

baseline
--------

Versioned requirement baselines for change management. Supports
ISO 26262-8 §9 configuration management requirements — snapshot the
current ``needs.json`` as a named baseline, list stored baselines, and
compute structured diffs between any two baselines.

Baselines are stored in ``.osqar-baselines/<tag>/`` within the project
directory, each containing a ``needs.json`` copy and a
``baseline-manifest.json`` with metadata.

See :doc:`lifecycle_management` for integrating baselines into your versioning and change control process.

Subcommands
^^^^^^^^^^^

- ``baseline snapshot`` — capture the current ``needs.json`` as a named baseline
- ``baseline list`` — list all stored baselines with metadata
- ``baseline diff`` — compute a structured diff between two baselines

baseline snapshot
^^^^^^^^^^^^^^^^^

Synopsis
^^^^^^^^

.. code-block:: console

  osqar baseline snapshot --tag <tag> [--project <dir>]
         [--message <text>] [--parent <tag>] [--needs-json <path>] [--force]

Options
^^^^^^^

- ``--tag``: required; baseline tag (alphanumeric, hyphens, dots, underscores)
- ``--project``: project directory (default: ``.``)
- ``--message``: human-readable description of this baseline
- ``--parent``: parent baseline tag (for lineage tracking)
- ``--needs-json``: path to needs.json (default: ``<project>/_build/html/needs.json``)
- ``--force``: overwrite existing baseline with the same tag

Examples
^^^^^^^^

.. code-block:: console

  # Create a baseline
  osqar baseline snapshot --tag v1.0 --message "Initial cJSON qualification baseline"

  # Snapshot with explicit needs.json path
  osqar baseline snapshot --tag v1.0 --needs-json ./_build/html/needs.json

baseline list
^^^^^^^^^^^^^

Synopsis
^^^^^^^^

.. code-block:: console

  osqar baseline list [--project <dir>]

Output shows each baseline's tag, date, need count, and message:

.. code-block:: text

  v1.0  2026-05-11    45 needs  Initial cJSON qualification baseline
  v1.1  2026-05-12    47 needs  Added UTF-16 validation requirements

baseline diff
^^^^^^^^^^^^^

Synopsis
^^^^^^^^

.. code-block:: console

  osqar baseline diff <tag_old> <tag_new> [--project <dir>]
         [--format {text,json}] [--verbose] [--json-report <path>]

Output
^^^^^^

**Text** (default) — summary counts plus per-need change details:

.. code-block:: text

  Baseline diff: v1.0 → v1.1
    45 → 47 needs (+2 added, 0 modified, 0 removed, 45 unchanged)

    [ADDED]    REQ_CJSON_UTF16_VALIDATION
               The parser shall reject invalid UTF-16 surrogate pairs

    [ADDED]    REQ_CJSON_UTF16_ENCODE
               UTF-16 encoding shall produce valid output per RFC 8259

**JSON** — structured report with ``schema: osqar.baseline_diff.v1``, counts,
and detailed ``added``/``removed``/``modified`` arrays with ``changes`` objects
tracking field-level deltas (``status``, ``links``, ``tags``, ``title``).

Examples
^^^^^^^^

.. code-block:: console

  # Text diff
  osqar baseline diff v1.0 v1.1

  # Verbose diff showing field-level changes
  osqar baseline diff v1.0 v1.1 --verbose

  # Machine-readable for CI
  osqar baseline diff v1.0 v1.1 --format json --json-report baseline_diff.json



.. _cli-gsn:

gsn
---

Generate GSN (Goal Structuring Notation) safety case diagrams and
specifications from ``.. safety-case::`` needs in a sphinx-needs
``needs.json`` export.

**Two backends:**

- ``plantuml`` (default) — produces a ``.puml`` file with GSN elements:
  goals (rectangles), strategies (hexagons), solutions (circles),
  context (rectangles), and assumptions (ellipses). Renderable via
  ``plantuml`` or directly embeddable in Sphinx via
  ``sphinxcontrib.plantuml``.
- ``gsn2x-yaml`` — produces a gsn2x-compatible YAML specification for the
  `jonasthewolf/gsn2x <https://github.com/jonasthewolf/gsn2x>`_ Rust binary.
  gsn2x renders **formally correct** GSN diagrams per the GSN Community
  Standard: parallelogram strategies, rounded-rectangle context nodes with
  side-connectors, solid hollow-head in-context-of arrows. Requires the
  gsn2x binary (~2.7 MB download from GitHub releases).

When ``--render`` is passed with the PlantUML backend, the ``.puml``
is rendered to PNG via the system ``plantuml`` binary.

Safety-case needs are identified by the ``SC_`` ID prefix.

See :doc:`using_the_boilerplate` for embedding GSN diagrams in your documentation workflow.

Subcommands
^^^^^^^^^^^

- ``gsn generate`` — generate a GSN diagram or specification from needs.json

Synopsis
^^^^^^^^

.. code-block:: console

  osqar gsn generate <needs_json> [--output <path>] [--backend {plantuml|gsn2x-yaml}] [--render]

Options
^^^^^^^

- ``needs_json``: path to ``needs.json`` produced by sphinx-needs
- ``--output``: output path (default: ``gsn_safety_case.puml`` for plantuml,
  ``gsn_safety_case.yaml`` for gsn2x-yaml)
- ``--backend``: output backend, ``plantuml`` (default) or ``gsn2x-yaml``
- ``--render``: also render to PNG/SVG via system ``plantuml`` or ``gsn2x`` binary
  (depending on ``--backend``). Requires ``apt install plantuml`` or ``gsn2x`` on PATH.

Example
^^^^^^^

.. code-block:: console

  # Generate PlantUML GSN diagram (default)
  osqar gsn generate ./_build/html/needs.json --output gsn_safety_case.puml

  # Generate and render to PNG
  osqar gsn generate ./_build/html/needs.json --render

  # Generate gsn2x YAML and render to SVG
  osqar gsn generate ./_build/html/needs.json --backend gsn2x-yaml --render

  # Generate gsn2x YAML only (no render)
  osqar gsn generate ./_build/html/needs.json --backend gsn2x-yaml

Backend Comparison
^^^^^^^^^^^^^^^^^^

.. list-table:: PlantUML vs gsn2x Backend
   :header-rows: 1
   :align: left

   * - Feature
     - ``plantuml`` (default)
     - ``gsn2x-yaml``
   * - Output format
     - ``.puml`` (PlantUML source)
     - ``.yaml`` (gsn2x spec)
   * - Rendered format
     - PNG (``--render``)
     - SVG (``--render``)
   * - Sphinx integration
     - ``.. plantuml::`` directive
       (``sphinxcontrib.plantuml``)
     - ``.. image::`` directive
       (pre-rendered SVG)
   * - Renderer dependency
     - ``plantuml`` (apt) + Graphviz
     - ``gsn2x`` binary (GitHub
       releases, ~2.7 MB)
   * - Goals
     - Green rectangles with
       ``<<goal>>`` stereotype
     - GSN-standard rectangles
   * - Strategies
     - Orange hexagons
       (no parallelogram shape)
     - GSN-standard
       **parallelograms** ✓
   * - Solutions
     - Blue circles ✓
     - GSN-standard circles ✓
   * - Context
     - Cyan rectangles with
       ``<<context>>`` stereotype
     - GSN-standard rounded
       rectangles ✓
   * - Assumptions
     - Yellow ellipses
       (via ``usecase`` shape)
     - GSN-standard ellipses ✓
   * - In-context-of edge
     - Dashed arrow with label
       ``context``
     - Solid hollow-head arrow ✓
   * - Supported-by edge
     - Solid arrow with label
       ``supported by``
     - Solid filled-head arrow ✓
   * - Auto-layout
     - Graphviz (via PlantUML)
     - Built-in layered layout
   * - Unicode / multiline
     - Full ✓
     - Limited (ASCII labels)
   * - CI availability
     - ``apt install plantuml``
       (standard package)
     - Download binary from
       GitHub releases
   * - GSN formal fidelity
     - Approximate (strategy
       shape differs, context
       shape differs)
     - **Formally correct** ✓
       (all element shapes
       match GSN standard)
   * - Best for
     - Quick diagrams, Sphinx
       embedding, CI without
       extra downloads
     - Formal safety case
       submissions, ISO 26262
       auditor review


.. _cli-sign:

sign
----

Cryptographically sign shipment manifests using GPG detached signatures.

Provides integrity *and authenticity* evidence for auditable shipments.
ISO 26262-8 §11.4.4 expects authenticity evidence for tool chains.

See :doc:`suppliers_guide` (supplier signing) and :doc:`integrators_guide` (verification).

Subcommands
^^^^^^^^^^^

- ``sign create`` — create a detached signature for a manifest file
- ``sign verify`` — verify a detached signature against a manifest

sign create
^^^^^^^^^^^

Synopsis
^^^^^^^^

.. code-block:: console

  osqar sign create --manifest <path> [--key <id>] [--output <path>] [--armor]

Options
^^^^^^^

- ``--manifest``: required; path to manifest file (e.g., ``SHA256SUMS``)
- ``--key``: GPG key ID or email to sign with (optional; uses default key if omitted)
- ``--output``: output signature path (default: ``<manifest>.sig``)
- ``--armor``: ASCII-armor the signature (``.asc`` extension)

sign verify
^^^^^^^^^^^

Synopsis
^^^^^^^^

.. code-block:: console

  osqar sign verify --manifest <path> [--signature <path>]

Options
^^^^^^^

- ``--manifest``: required; path to signed manifest file
- ``--signature``: path to signature file (default: ``<manifest>.sig``)

Examples
^^^^^^^^

.. code-block:: console

  # Sign a shipment manifest
  osqar sign sign --manifest _build/html/SHA256SUMS --key qualification@example.com

  # Verify before unpacking a received shipment
  osqar sign verify --manifest _build/html/SHA256SUMS


.. _cli-workspace-combine:

workspace combine
^^^^^^^^^^^^^^^^^

Merge ``needs.json`` exports from multiple OSQAr projects into a single
namespace-prefixed needs.json for cross-project traceability.

Each project's needs are prefixed with ``<project-name>:`` to avoid ID
collisions. Links are rewritten to use prefixed IDs within each project's
scope.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar workspace combine [--root <dir>] [--project <dir> ...] [--output <path>]

Options
^^^^^^^

- ``--root``: root directory containing project subdirectories (default: ``.``)
- ``--project``: explicit project directory (repeatable; auto-discovered if omitted)
- ``--output``: output path (default: ``_build/workspace/needs.json``)

Auto-discovery looks for subdirectories containing ``conf.py`` and ``index.rst``.

Example
^^^^^^^

.. code-block:: console

  # Combine example projects under examples/
  osqar workspace combine --root examples

  # Combine explicit projects
  osqar workspace combine --project ./osqar-cjson --project ./osqar-base64 --output combined.json


workspace traceability
^^^^^^^^^^^^^^^^^^^^^^

Run traceability checks on a combined workspace ``needs.json``.

Synopsis
^^^^^^^^

.. code-block:: console

  osqar workspace traceability [--needs-json <path>] [--json-report <path>]
         [--req-prefix <prefix> ...] [--arch-prefix <prefix> ...]
         [--enforce-req-has-test]

Options
^^^^^^^

- ``--needs-json``: path to combined needs.json (default: ``_build/workspace/needs.json``)
- ``--json-report``: write JSON traceability report
- ``--req-prefix``, ``--arch-prefix``, ``--test-prefix``, ``--code-prefix``: ID prefix overrides (repeatable)
- ``--enforce-req-has-test``: also enforce REQ_* → TEST_* coverage

Example
^^^^^^^

.. code-block:: console

  # Combine first, then check traceability
  osqar workspace combine --root examples
  osqar workspace traceability
