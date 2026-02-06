Collaboration workflows (multi-user)
====================================

OSQAr is **documentation-first**. That makes collaboration scalable *if* you treat the
Sphinx sources as controlled engineering artifacts (not as free-form prose).

This chapter describes practical branching/merging strategies and conventions that
reduce merge conflicts and keep traceability stable for large teams.

Principles
----------

- **Keep IDs stable**: requirement/architecture/test IDs (``REQ_*``, ``ARCH_*``, ``TEST_*``)
  are part of the contract. Never recycle IDs.
- **Prefer additive changes**: add new needs and new sections instead of rewriting existing
  paragraphs.
- **Split work by files**: parallel work scales when people do not edit the same ``.rst`` files.
- **Automate checks**: run docs builds and traceability checks in CI for every change.

Repository layout for parallel work
-----------------------------------

To minimize conflicts, organize content so contributors naturally touch different files:

- One chapter per concern (requirements / architecture / verification / lifecycle / collaboration).
- Split large chapters into multiple files and include them from a stable index page.
- Prefer “append-only” files for requirements lists (see below).

Typical pattern:

.. code-block:: text

   requirements/
     safety_requirements.rst
     functional_requirements.rst
     interfaces.rst
   architecture/
     system_context.rst
     component_decomposition.rst
   verification/
     verification_plan.rst
     test_results.rst

Use a stable top-level toctree that rarely changes, and let subtrees grow.

Branching strategies
--------------------

Two common approaches work well with OSQAr. Choose one and apply it consistently.

Trunk-based development (recommended for most teams)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- ``main`` is always releasable.
- Developers branch from ``main`` and open small pull requests.
- Merge frequently (at least daily) to reduce drift and conflicts.

Guidelines:

- Keep PRs small (e.g., one feature or one document area).
- Prefer **squash merge** for clean history, unless you need full commit lineage.
- Use short-lived feature branches: ``feature/<topic>``.

Release branches (useful when multiple releases are supported)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- ``main`` continues forward.
- Cut a branch ``release/x.y`` when you need stabilization.
- Backport fixes via cherry-picks.

Guidelines:

- Tag releases (e.g., ``v0.2.2``) and keep the shipped documentation reproducible.
- Avoid large refactors on release branches.

Merging strategies
------------------

- Prefer **merge by pull request**, not direct pushes to protected branches.
- Use a consistent merge mode:

  - **Squash merge**: good default; one commit per PR, easier audit trail.
  - **Merge commit**: useful when you want to preserve a topic branch structure.

- Avoid rebasing shared branches after review starts (it rewrites history and complicates review).

How to minimize merge conflicts
-------------------------------

RST (reStructuredText)
^^^^^^^^^^^^^^^^^^^^^^

- Avoid re-wrapping paragraphs for style changes; it causes noisy diffs.
- Keep lists stable: append items instead of reordering.
- If two people need to edit the same chapter, split it first.

Sphinx-needs objects
^^^^^^^^^^^^^^^^^^^^

- Treat IDs as immutable. If wording changes, keep the same ``:id:``.
- Add new requirements as new needs; avoid “editing history into the same need” unless
  it is truly the same requirement.
- Maintain consistent prefixes (``REQ_SAFETY_*``, ``REQ_FUNC_*``, ``ARCH_*``, ``TEST_*``).

Diagrams (PlantUML)
^^^^^^^^^^^^^^^^^^^

- Prefer one diagram per file.
- Avoid large diagram rewrites; add a new diagram revision (e.g., ``03_context_v2.puml``)
  if needed.

Generated artifacts
^^^^^^^^^^^^^^^^^^^

- Never commit build outputs (``_build/``, ``target/``, ``build/``).
- Treat shipments (evidence bundles) as **immutable** after creation.

Collaborating at scale
----------------------

Roles and review gates
^^^^^^^^^^^^^^^^^^^^^^

For industry-scale collaboration, define a simple set of gates:

- **Author**: proposes change via PR.
- **Reviewer**: checks clarity, correctness, and traceability links.
- **Integrator**: confirms evidence is consistent and reproducible.

Recommended CI checks:

- ``sphinx-build -W`` to treat warnings as errors
- traceability check on exported ``needs.json``
- checksum generation/verification for example shipments (if you publish them)

.. _ci-setup:

CI setup (GitHub Actions)
-------------------------

This repository uses GitHub Actions to continuously validate the boilerplate and to
demonstrate “evidence shipment” generation.

Workflow definitions:

- ``.github/workflows/ci.yml`` (Tests and Example Shipments)
- ``.github/workflows/pages-deploy.yml`` (GitHub Pages)

What the CI runs
^^^^^^^^^^^^^^^^

- Python checks (matrix): install via Poetry, run ``pytest``, build the Python demo example docs.
- Traceability validation: run ``./osqar traceability`` on the exported ``needs.json``.
- Integrity metadata: generate and verify ``SHA256SUMS`` manifests for built documentation outputs.

Reproducible example shipments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The CI workflow builds deterministic archives for the native examples (C/C++/Rust):

- Sets ``SOURCE_DATE_EPOCH`` (using the latest git commit timestamp).
- Enables reproducible mode via ``OSQAR_REPRODUCIBLE=1``.
- Produces per-example shipment archives and a combined example workspace archive, each with a ``.sha256`` file.

In GitHub Actions, download the artifact named ``osqar-example-workspace`` from the
``Tests and Example Shipments`` workflow run.

GitHub Pages publishing
^^^^^^^^^^^^^^^^^^^^^^^

The Pages workflow builds the framework docs and publishes rendered examples under ``/examples/``.
It also runs the example end-to-end scripts (tests → evidence files → docs) so the published site
includes embedded test results and evidence snapshots.

Working on multiple subprojects in parallel
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When multiple teams produce shipments simultaneously:

- Standardize naming for shipments: ``<supplier>_<component>_<version>``.
- Include ``osqar_project.json`` in each shipment to record origin, URLs, and descriptive metadata.
- Use ``./osqar workspace intake`` to archive and summarize received shipments.

Change control tips
-------------------

- Record user-facing changes in ``CHANGELOG.md``.
- Keep a stable requirement ID namespace and allocate ID ranges if multiple teams author requirements.
- For safety-relevant changes, require an explicit review and update lifecycle records accordingly.
