=============
CLI Reference
=============

OSQAr ships a small, stdlib-only CLI to scaffold projects and to run common evidence workflows
(build docs, validate traceability, generate/verify checksums, supplier/integrator intake).

This page is the **command reference**. For the recommended workflows and the rationale behind them,
see :doc:`using_the_boilerplate`.

Invocation
==========

Recommended (PyPI / pipx)
-------------------------

Install and run OSQAr as a normal CLI tool:

- Install: ``pipx install osqar``
- Invoke: ``osqar <command> ...``

When building docs, OSQAr will automatically use a project’s Poetry environment (``poetry run ...``)
if it detects a Poetry-managed project and ``poetry`` is available.

Repo-root wrappers (contributors)
---------------------------------

If you are working from a git clone and have not installed OSQAr via pipx, you can use the repo-root wrappers:

- Linux/macOS: ``./osqar <command> ...``
- Windows: ``.\osqar.cmd <command> ...`` or ``.\osqar.ps1 <command> ...``

Common defaults
===============

Some commands are designed to be concise for the “run it in the current folder” case:

- ``build-docs`` defaults to ``--project .`` and outputs to ``<project>/_build/html``.

Configuration and hooks
=======================

OSQAr supports optional JSON configuration files to make workflows extensible for small and large projects.

For a detailed reference (supported keys, hook events, and examples), see :doc:`configuration_and_hooks`.

Project config: ``osqar_project.json`` (supplier/dev side)
-------------------------------------------------------------------------------

Placed in the **project root**.

Supported keys (v1-style, best-effort):

- ``commands.docs``: override how docs are built (used by ``shipment build-docs`` and ``shipment prepare``)
- ``commands.test``: override how tests/build are run (used by ``shipment run-tests`` and ``shipment prepare``)
- ``commands.build``: used by ``shipment run-build``
- ``hooks.pre`` / ``hooks.post``: optional command(s) to run around OSQAr events

Example:

.. code-block:: json

   {
     "commands": {
       "test": "OSQAR_REPRODUCIBLE=1 ./build-and-test.sh",
       "docs": "poetry run sphinx-build -b html . _build/html"
     },
     "hooks": {
       "pre": {
         "shipment.prepare": "echo pre-prepare"
       },
       "post": {
         "shipment.prepare": ["echo post-prepare", "echo done"]
       }
     }
   }

Workspace config: ``osqar_workspace.json`` (integrator side)
-------------------------------------------------------------------------------

Placed in a **trusted integrator workspace root**.

Security note:

- Treat configs inside received/shipped bundles as untrusted. Only use workspace config from a trusted location.

Common flags
------------

- ``--config <path>``: override config file path (project or workspace, depending on the command)
- ``--no-hooks``: disable all pre/post hooks for the invocation
- Environment kill switch: set ``OSQAR_DISABLE_HOOKS=1`` to disable hooks globally

Execution model:

- Hook and command strings are executed without a shell (argv splitting via Python). If you need shell features (pipes, ``&&``), wrap explicitly, e.g. ``bash -lc '...your pipeline...'``.

Hook events
-----------

Hook event names are simple strings; current events include:

- ``shipment.prepare``, ``shipment.build-docs``, ``shipment.run-tests``
- ``shipment.verify`` (integrator-side)
- ``workspace.report``, ``workspace.verify``, ``workspace.verify.shipment``, ``workspace.intake``

Top-level commands
==================

build-docs
----------

Build Sphinx HTML documentation for a shipment project (shorthand for ``shipment build-docs``).

Arguments:

- ``--project``: project directory (default: ``.``; must contain ``conf.py`` and ``index.rst``)
- ``--config``: override project config JSON path (default: ``<project>/osqar_project.json``)
- ``--no-hooks``: disable pre/post hooks for this command
- ``--output``: output directory (default: ``<project>/_build/html``)
- ``--open``: open the built ``index.html`` in your default browser

Examples:

- Build docs for the current project: ``osqar build-docs``
- Build docs for an example: ``osqar build-docs --project examples/c_hello_world``
- Build and open immediately: ``osqar build-docs --open``

open-docs
---------

Open built HTML documentation (``index.html``) in your default browser.

Defaults:

- Opens ``<project>/_build/html/index.html`` (default project: ``.``).

Examples:

- Open the current project docs: ``osqar open-docs``
- Open an example’s docs: ``osqar open-docs --project examples/python_hello_world``
- Open a specific shipment directory: ``osqar open-docs --shipment examples/python_hello_world/_build/html``

setup
-----

Verify, extract, and then verify a downloaded shipment/workspace ZIP.

Intent:

- Make GitHub Release assets usable immediately (especially the combined example workspace).
- Verify a sibling checksum file (``.sha256`` / ``.zip.sha256``) when present.

Behavior:

- If a checksum file is found next to the ZIP, OSQAr verifies it and fails on mismatch.
- If no checksum file is present, OSQAr emits a warning and continues.
- The ZIP is extracted into a directory and OSQAr runs the appropriate verification command:

  - Workspace bundle: ``osqar workspace verify``
  - Shipment bundle: ``osqar shipment verify``

Arguments:

- ``zip``: path to a shipment/workspace ZIP
- ``--output``: extraction directory (default: ``<zip path without .zip>``)
- ``--force``: overwrite the output directory if it exists

Example (combined example workspace from Releases):

- ``osqar setup osqar_example_workspace_<tag>.zip``

doctor
------

Run a full status report for debugging.

Intent:

- **Before shipping**: validate the local build environment (Poetry/Sphinx/PlantUML) and perform best-effort checks on the built shipment directory.
- **After receiving**: diagnose a received shipment directory without requiring build tools.

Checks (best-effort):

- Poetry availability (if the project is Poetry-managed)
- Sphinx importability in the environment used by ``build-docs``
- PlantUML availability (``plantuml`` command or ``PLANTUML_JAR`` + Java)
- Shipment consistency (if a shipment directory is found/provided): ``index.html``, ``needs.json``, ``traceability_report.json``, ``SHA256SUMS``, ``osqar_project.json``

Machine-readable output:

- Use ``--json-report <path>`` to write a structured JSON report (schema: ``osqar.doctor_report.v1``).

Examples:

- Check the current project: ``osqar doctor``
- Check an example: ``osqar doctor --project examples/python_hello_world``
- Also check traceability if a built ``needs.json`` is present: ``osqar doctor --traceability``
- Diagnose a received shipment directory (skip environment checks): ``osqar doctor --shipment /path/to/shipment --skip-env-checks --json-report doctor_report.json``

new
---

Create a new OSQAr project from a language template.

Required arguments:

- ``--language``: one of ``c``, ``cpp``, ``python``, ``rust``
- ``--name``: project name (used as the default folder name)

Optional arguments:

- ``--destination``: destination directory (default: ``./<name>``)
- ``--template``: ``basic`` (default) or ``example``
- ``--force``: overwrite an existing destination

Example:

- ``osqar new --language c --name MySEooC --destination ../MySEooC``

traceability
------------

Run traceability checks on an exported ``needs.json``.

Required arguments:

- ``needs_json``: path to ``needs.json``

Optional arguments:

- ``--json-report``: write report JSON
- ``--enforce-req-has-test``
- ``--enforce-arch-traces-req``
- ``--enforce-test-traces-req``

Example:

- ``osqar traceability ./_build/html/needs.json --json-report ./_build/html/traceability_report.json``

code-trace
----------

Scan implementation and test sources for need IDs (e.g., ``REQ_*``, ``ARCH_*``, ``TEST_*``) embedded in comments.

Intent:

- Keep the docs-based traceability chain (``needs.json``) connected to the *actual code*.
- Optionally enforce that every ``REQ_*`` / ``ARCH_*`` is mentioned at least once in implementation sources and every ``TEST_*`` at least once in test sources.

Key inputs:

- ``--root``: project root to scan (defaults to ``.``)
- ``--needs-json``: expected IDs source (optional for reporting; required for enforcement)

Examples:

- Generate a report (non-failing):

  - ``osqar code-trace --root . --needs-json ./_build/html/needs.json --json-report ./_build/html/code_trace_report.json``

- Enforce “REQ/ARCH appear in implementation, TEST appears in tests”:

  - ``osqar code-trace --root . --needs-json ./_build/html/needs.json --enforce-req-in-impl --enforce-arch-in-impl --enforce-test-in-tests``

checksum
--------

Generate or verify checksum manifests.

Subcommands:

- ``checksum generate --root <dir> --output <manifest> [--exclude <glob> ...]``
- ``checksum verify --root <dir> --manifest <manifest> [--exclude <glob> ...]``

Optional arguments (both subcommands):

- ``--json-report <path>``: write a machine-readable JSON report (schema: ``osqar.checksums_report.v1``)

Example:

- ``osqar checksum generate --root ./_build/html --output ./_build/html/SHA256SUMS``

Shipment commands
=================

The ``shipment`` command group contains operations that act on a project directory or a built
shipment directory (usually ``<project>/_build/html``).

Common subcommands:

- ``shipment list``: discover shipment projects under a directory
- ``shipment build-docs``: same as top-level ``build-docs``
- ``shipment prepare``: generalized “build + traceability + checksums (+ archive)” workflow
- ``shipment verify``: verify a **received** shipment directory (checksums, optional traceability re-check)
- ``shipment traceability``: validate a built shipment directory
- ``shipment checksums``: generate/verify checksums for a shipment directory
- ``shipment clean``: remove generated outputs (conservative by default)
- ``shipment run-tests``: run a project’s ``build-and-test.sh`` (best run on POSIX/WSL2)
- ``shipment run-build``: run a per-project build command (configured in the project root)
- ``shipment metadata write``: write ``osqar_project.json`` into a shipment root

Workspace commands
==================

The ``workspace`` command group operates on multiple shipments/projects in a directory.

Common subcommands:

- ``workspace list``: discover shipments under a root directory (by scanning for ``SHA256SUMS``)
- ``workspace report``: generate a Subproject overview (HTML + JSON) without copying shipments
	(use ``--open`` to open it in a browser)
- ``workspace diff``: diff two workspace reports (e.g., ``subproject_overview.json``)
- ``workspace verify``: verify many shipments (checksums and optionally traceability)
- ``workspace intake``: ingest multiple shipments into an archive directory and generate a consolidated overview

For CI/non-interactive usage:

- Use ``workspace report`` (without ``--open``) to avoid opening a browser and only print the built ``index.html`` path.

Use ``osqar <command> --help`` to see the full set of options for these workflows.

Workspace examples:

- List shipments under a folder: ``osqar workspace list --root intake/received --recursive``
- Generate an overview without copying: ``osqar workspace report --root intake/received --recursive --output intake/overview``
- Generate an overview and also verify checksums + traceability: ``osqar workspace report --root intake/received --recursive --output intake/overview --checksums --traceability``
- Generate and open an HTML overview: ``osqar workspace report --root intake/received --recursive --output intake/overview --open``
- Generate/open and also show checksums + traceability status: ``osqar workspace report --root intake/received --recursive --output intake/overview --checksums --traceability --open``
- Run with an explicit workspace config: ``osqar workspace report --root intake/received --config osqar_workspace.json --output intake/overview``
- Diff two overviews: ``osqar workspace diff intake/overview/subproject_overview.json intake/overview_new/subproject_overview.json``

Per-project build command
=========================

In addition to ``shipment run-tests``, OSQAr can run a per-project build command.

Configure it by placing an ``osqar_project.json`` in the **project root** (not the shipped directory) and setting:

- ``commands.build`` (string; executed in the project directory)

Example:

- ``osqar shipment run-build --project examples/python_hello_world``
