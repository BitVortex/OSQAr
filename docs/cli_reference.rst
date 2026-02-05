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

Examples:

- Build docs for the current project: ``./osqar build-docs``
- Build docs for an example: ``./osqar build-docs --project examples/c_hello_world``

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
- ``shipment traceability``: validate a built shipment directory
- ``shipment checksums``: generate/verify checksums for a shipment directory
- ``shipment clean``: remove generated outputs (conservative by default)
- ``shipment run-tests``: run a project’s ``build-and-test.sh`` (best run on POSIX/WSL2)
- ``shipment metadata write``: write ``osqar_project.json`` into a shipment root

Supplier / integrator / workspace
=================================

OSQAr also provides higher-level workflows:

- Supplier: ``supplier prepare`` (build docs, traceability, checksums, optional archive)
- Integrator: ``integrator verify`` (verify checksums and/or traceability)
- Workspace: ``workspace intake`` (ingest multiple shipments and generate a consolidated overview)

Use ``./osqar <command> --help`` to see the full set of options for these workflows.
