Multi-project workflows (integrators)
=====================================

This section describes how to work with multiple supplier projects/shipments at once.
The goal is to keep evidence intake scalable and repeatable, while preserving integrity and traceability.

Quick start (integrator)
------------------------

This is the simplest repeatable workflow when you receive multiple shipments:

.. code-block:: bash

  # 1) Put supplier shipments under intake/received/<name>/
  # 2) Verify + archive them into a dated intake folder
  ./osqar workspace intake \
    --root intake/received \
    --recursive \
    --output intake/archive/2026-02-01 \
    --traceability

Then open the generated overview:

.. code-block:: bash

  open intake/archive/2026-02-01/subproject_overview.md

Concepts
--------

**Project**
    A Sphinx documentation project that contains at least ``conf.py`` and ``index.rst``.

**Shipment**
    A directory that a supplier provides to an integrator as an evidence bundle.
    In OSQAr, a shipment is typically the Sphinx HTML output directory
    (e.g. ``<project>/_build/html``) and contains:

    - ``needs.json`` (exported by ``sphinx-needs``)
    - ``SHA256SUMS`` (integrity manifest)
    - ``traceability_report.json`` (optional but recommended)
    - Optional test reports (e.g. JUnit XML)

Recommended folder layout (integrator)
--------------------------------------

Keep supplier inputs immutable and separate from your integrator-side processing.
A simple layout that works well for multi-project intake:

.. code-block:: text

  intake/
  received/              # immutable: supplier-provided shipments
  archive/               # immutable: your frozen intake archive(s)
  working/               # mutable: scratch, analysis, combined views
  reports/               # integrator-side summaries (JSON/CSV/etc)

Typical process
---------------

1. Receive shipments into ``received/`` (do not modify them).
2. Verify integrity (checksums) before any further processing.
3. Optionally run an integrator-side traceability check.
4. Copy verified shipments into a dated archive and write an intake report.
5. Build combined views (indexes, dashboards, consolidated evidence) from the archive.

What the intake produces
------------------------

An intake directory is meant to be self-contained and audit-friendly:

.. code-block:: text

   intake/archive/2026-02-01/
     intake_report.json
     subproject_overview.json
     subproject_overview.md
     SHA256SUMS
     shipments/
       <shipment-name>/
         index.html
         needs.json
         osqar_project.json
         ... (rendered docs and shipped artifacts)
     reports/
       <shipment-name>/
         traceability_report.integrator.json

The file ``subproject_overview.md`` is intended as the main human entrypoint.

Batch verification (CLI)
------------------------

To verify many shipments at once (integrator side), use the workspace commands.
They discover shipment directories by scanning for ``SHA256SUMS``.

.. code-block:: bash

   # Verify all shipments under a folder
   ./osqar workspace verify \
     --root intake/received \
     --recursive

   # Also run traceability checks (writes integrator-side reports alongside your archive/intake output)
   ./osqar workspace verify \
     --root intake/received \
     --recursive \
     --traceability

Intake + archiving (CLI)
------------------------

To create an immutable intake archive from multiple shipments:

.. code-block:: bash

   ./osqar workspace intake \
     --root intake/received \
     --recursive \
     --output intake/archive/2026-02-01 \
     --traceability

The intake output is structured so that the copied shipments remain byte-identical,
while integrator-side reports are written separately.

Practical naming convention
---------------------------

To keep multi-project work manageable, ensure shipment folders are unique and human-readable.
Good patterns:

- ``<supplier>_<component>_<version>``
- ``<supplier>_<component>_<version>_<platform>``

Avoid ambiguous names like ``shipment/`` or ``output/``.

Shipment metadata (supplier-provided)
-------------------------------------

Suppliers can include a machine-readable metadata file in the shipment root:

- ``osqar_project.json``

This can contain descriptive metadata as well as URLs (repository, homepage, documentation)
and an explicit origin (e.g., VCS URL + revision). Integrators can use this to record
where a shipment came from and how it maps back to source control.

Write metadata into a shipment directory:

.. code-block:: bash

   ./osqar shipment metadata write \
     --shipment <project>/_build/html \
     --name "My Component" \
     --version "1.2.3" \
     --description "Safety element out of context (SEooC)" \
     --url repository=https://example.com/repo.git \
     --url documentation=https://example.com/docs \
     --origin url=https://example.com/repo.git \
     --origin revision=abc123

Subproject overview (integrator output)
---------------------------------------

When you run an intake, OSQAr generates a **Subproject overview** in the intake output:

- ``subproject_overview.json``
- ``subproject_overview.md``

These summarize all projects/shipments, their verification status, and (if present)
their supplier-provided metadata (including origin and URLs).

The overview additionally includes:

- A link to the archived HTML entrypoint (``shipments/<name>/index.html``), if present
- A small needs export summary derived from ``needs.json`` (total needs, REQ/ARCH/TEST counts)

If a supplier does not provide ``osqar_project.json``, the overview still works, but it will
have less context about origin/URLs.

Notes and good practices
------------------------

- Verify ``SHA256SUMS`` *before* running any analysis tools.
- Do not regenerate supplier manifests; verify them.
- Keep integrator-generated artifacts (reports, dashboards) outside the shipment tree.
- Prefer deterministic naming (supplier, component, version) for shipment folders.
