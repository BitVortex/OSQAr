=======================
Configuration and hooks
=======================

OSQAr supports optional JSON configuration files so teams can plug in their own build/test/verification tooling
while keeping OSQAr’s evidence structure, traceability checks, and checksum-based integrity verification.

This page describes the **supported keys**, how commands are executed, and which hook events exist.

Overview
========

Two configuration files are supported:

- ``osqar_project.json`` (project-side; supplier/dev)
- ``osqar_workspace.json`` (workspace-side; integrator)

Both are optional. OSQAr works without them.

Security model (important)
==========================

- Treat configuration and hooks inside received/shipped bundles as **untrusted input**.
- Integrators should load workspace config from a **trusted** location (via ``--config-root`` / ``--config``)
  and avoid executing commands from supplier-provided files.

Execution model
===============

Configured commands and hooks are executed **without a shell** (argv splitting via Python).

- If you need shell features (pipes, ``&&``, redirections), wrap explicitly, e.g.::

    bash -lc 'set -euo pipefail; your_command | other_command && echo done'

Disabling hooks
===============

You can disable hooks in two ways:

- Per invocation: pass ``--no-hooks``
- Globally: set environment variable ``OSQAR_DISABLE_HOOKS=1``

Project config: ``osqar_project.json``
======================================

Location
--------

Place ``osqar_project.json`` in the **project root**.

How it is used
--------------

Project config is read by project-side commands such as:

- ``shipment build-docs`` (and top-level ``build-docs``)
- ``shipment run-build``
- ``shipment run-tests``
- ``shipment prepare``

Supported keys
--------------

OSQAr reads the file as a JSON object. Unknown keys are ignored.

Metadata keys (optional)
^^^^^^^^^^^^^^^^^^^^^^^^

These are useful for integrators and workspace overviews:

- ``name`` (string)
- ``id`` (string)
- ``version`` (string)
- ``description`` (string)
- ``urls`` (object/dict of string → string)
- ``origin`` (object/dict of string → string; common keys: ``url``, ``revision``)

Command overrides
^^^^^^^^^^^^^^^^^

Use ``commands`` to override OSQAr’s default execution for project-specific steps:

- ``commands.docs`` (string): docs build command executed in the project directory
- ``commands.test`` (string): test/build command executed in the project directory
- ``commands.build`` (string): build-only command for ``shipment run-build``

Example:

.. code-block:: json

   {
     "name": "My Component",
     "version": "1.2.3",
     "commands": {
       "test": "OSQAR_REPRODUCIBLE=1 ./build-and-test.sh",
       "docs": "poetry run sphinx-build -b html . _build/html",
       "build": "cmake -S . -B build && cmake --build build"
     }
   }

Hooks
^^^^^

Hooks allow you to run additional commands before/after OSQAr events.

Structure:

- ``hooks.pre``: object mapping ``<event>`` → command or list of commands
- ``hooks.post``: object mapping ``<event>`` → command or list of commands

Example:

.. code-block:: json

   {
     "hooks": {
       "pre": {
         "shipment.prepare": "echo pre-prepare"
       },
       "post": {
         "shipment.prepare": ["echo post-prepare", "echo done"]
       }
     }
   }

Workspace config: ``osqar_workspace.json``
==========================================

Location
--------

Place ``osqar_workspace.json`` in a trusted workspace root.

How it is used
--------------

Workspace config is read by workspace-side commands such as:

- ``workspace report``
- ``workspace verify``
- ``workspace intake``

It is also used by ``shipment verify`` when invoked with an explicit workspace root:

- ``shipment verify --config-root <trusted_root>``

Supported keys
--------------

Defaults
^^^^^^^^

``defaults.exclude`` can define default exclude globs for checksum verification:

.. code-block:: json

   {
     "defaults": {
       "exclude": ["**/.DS_Store", "**/__pycache__/**"]
     }
   }

Hooks
^^^^^

Same structure as project hooks (``hooks.pre`` / ``hooks.post``), but intended for integrator workflows.

Hook events
===========

Event names are simple strings.

Project-side events:

- ``shipment.build-docs``
- ``shipment.run-tests``
- ``shipment.prepare``

Integrator/workspace-side events:

- ``shipment.verify``
- ``workspace.report``
- ``workspace.verify``
- ``workspace.verify.shipment``
- ``workspace.intake``

Extra integrator verification commands
======================================

Integrators can attach additional per-shipment verification commands (repeatable) that run after OSQAr’s
built-in verification (checksums + optional traceability)::

  ./osqar shipment verify \
    --shipment /path/to/shipment \
    --config-root /trusted/workspace \
    --verify-command "python -m my_company.audit_check" \
    --verify-command "bash -lc 'my_scanner --input . --strict'"

The same option exists for batch verification:

- ``./osqar workspace verify --verify-command '<cmd>'``
