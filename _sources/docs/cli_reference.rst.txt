=============
CLI Reference
=============

OSQAr ships a small, stdlib-only CLI to scaffold projects and to run common evidence workflows
(build docs, validate traceability, generate/verify checksums, supplier/integrator intake).

This page is the **command reference**. For the recommended workflows and the rationale behind them,
see :doc:`using_the_boilerplate`.

Invocation
==========

Recommended (repo root)
-----------------------

- Linux/macOS: ``./osqar <command> ...``
- Windows: ``.\osqar.cmd <command> ...`` or ``.\osqar.ps1 <command> ...``

The wrapper prefers Poetry-managed execution when available.

Fallback (explicit Poetry invocation)
-------------------------------------

If you prefer not to use the wrapper, run:

- ``poetry run python -m tools.osqar_cli <command> ...``

Common defaults
===============

Some commands are designed to be concise for the “run it in the current folder” case:

- ``build-docs`` defaults to ``--project .`` and outputs to ``<project>/_build/html``.

Top-level commands
==================

build-docs
----------

Build Sphinx HTML documentation for a shipment project (shorthand for ``shipment build-docs``).

Arguments:

- ``--project``: project directory (default: ``.``; must contain ``conf.py`` and ``index.rst``)
- ``--output``: output directory (default: ``<project>/_build/html``)
- ``--open``: open the built ``index.html`` in your default browser

Examples:

- Build docs for the current project: ``./osqar build-docs``
- Build docs for an example: ``./osqar build-docs --project examples/c_hello_world``
- Build and open immediately: ``./osqar build-docs --open``

open-docs
---------

Open built HTML documentation (``index.html``) in your default browser.

Defaults:

- Opens ``<project>/_build/html/index.html`` (default project: ``.``).

Examples:

- Open the current project docs: ``./osqar open-docs``
- Open an example’s docs: ``./osqar open-docs --project examples/python_hello_world``
- Open a specific shipment directory: ``./osqar open-docs --shipment examples/python_hello_world/_build/html``

doctor
------

Run a quick diagnostic of common environment/setup issues.

Checks (best-effort):

- Poetry availability (if the project is Poetry-managed)
- Sphinx importability in the environment used by ``build-docs``
- PlantUML availability (``plantuml`` command or ``PLANTUML_JAR`` + Java)

Examples:

- Check the current project: ``./osqar doctor``
- Check an example: ``./osqar doctor --project examples/python_hello_world``
- Also check traceability if a built ``needs.json`` is present: ``./osqar doctor --traceability``

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

- ``./osqar new --language c --name MySEooC --destination ../MySEooC``

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

- ``./osqar traceability ./_build/html/needs.json --json-report ./_build/html/traceability_report.json``

checksum
--------

Generate or verify checksum manifests.

Subcommands:

- ``checksum generate --root <dir> --output <manifest> [--exclude <glob> ...]``
- ``checksum verify --root <dir> --manifest <manifest> [--exclude <glob> ...]``

Example:

- ``./osqar checksum generate --root ./_build/html --output ./_build/html/SHA256SUMS``

Shipment commands
=================

The ``shipment`` command group contains operations that act on a project directory or a built
shipment directory (usually ``<project>/_build/html``).

Common subcommands:

- ``shipment list``: discover shipment projects under a directory
- ``shipment build-docs``: same as top-level ``build-docs``
- ``shipment prepare``: generalized “build + traceability + checksums (+ archive)” workflow
- ``shipment verify``: generalized “verify checksums (+ traceability)” workflow
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
- ``workspace report``: generate a Subproject overview (Markdown + JSON) without copying shipments
- ``workspace open``: generate a Subproject overview and open an HTML version built via Sphinx (theme-aligned and shows OK/FAIL/skipped status for enabled checks)
- ``workspace diff``: diff two workspace reports (e.g., ``subproject_overview.json``)
- ``workspace verify``: verify many shipments (checksums and optionally traceability)
- ``workspace intake``: ingest multiple shipments into an archive directory and generate a consolidated overview

Use ``./osqar <command> --help`` to see the full set of options for these workflows.

Workspace examples:

- List shipments under a folder: ``./osqar workspace list --root intake/received --recursive``
- Generate an overview without copying: ``./osqar workspace report --root intake/received --recursive --output intake/overview``
- Generate an overview and also verify checksums + traceability: ``./osqar workspace report --root intake/received --recursive --output intake/overview --checksums --traceability``
- Generate and open an HTML overview: ``./osqar workspace open --root intake/received --recursive``
- Generate/open and also show checksums + traceability status: ``./osqar workspace open --root intake/received --recursive --checksums --traceability``
- Diff two overviews: ``./osqar workspace diff intake/overview/subproject_overview.json intake/overview_new/subproject_overview.json``

Per-project build command
=========================

In addition to ``shipment run-tests``, OSQAr can run a per-project build command.

Configure it by placing an ``osqar_project.json`` in the **project root** (not the shipped directory) and setting:

- ``commands.build`` (string; executed in the project directory)

Example:

- ``./osqar shipment run-build --project examples/python_hello_world``
