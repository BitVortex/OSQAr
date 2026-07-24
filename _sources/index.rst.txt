OSQAr (Open Safety Qualification Architecture)
==============================================

OSQAr is a documentation-first framework for producing, verifying, and integrating **auditable evidence shipments** for safety/compliance work.

A shipment is a reviewable bundle containing **Sphinx documentation with traceability**, plus **implementation**, **tests**, and **verification reports** — all integrity-protected with checksum manifests.

.. toctree::
   :maxdepth: 2
   :caption: 🚀 Getting Started
   :hidden:

   docs/getting_started
   docs/using_the_boilerplate
   docs/project_setup_from_scratch

.. toctree::
   :maxdepth: 1
   :caption: 📖 Guides (by role)
   :hidden:

   docs/suppliers_guide
   docs/integrators_guide

.. toctree::
   :maxdepth: 1
   :caption: 🏢 Professional Deployment
   :hidden:

   docs/lifecycle_management
   docs/multi_project_workflows
   docs/collaboration_workflows
   docs/ci_integration

.. toctree::
   :maxdepth: 1
   :caption: 🔧 Reference
   :hidden:

   docs/cli_reference
   docs/configuration_and_hooks
   docs/tool_reliance_boundary
   docs/evidence_acceptance
   docs/iso26262_reference_catalog
   docs/typed_traceability
   docs/release_manifest

.. toctree::
   :maxdepth: 1
   :caption: 📦 Examples
   :hidden:

   examples/index

.. toctree::
   :maxdepth: 1
   :caption: 🧠 Agent Skills
   :hidden:

   docs/agent_skills_usage

🚀 Getting Started
==================

- :doc:`docs/getting_started` — **start here**: what OSQAr is, install, first shipment in 5 minutes
- :doc:`docs/using_the_boilerplate` — comprehensive guide: mental model, terms, workflow recipes
- :doc:`docs/project_setup_from_scratch` — scaffold a new project or migrate an existing one

📖 Guides (by role)
===================

- :doc:`docs/suppliers_guide` — produce auditable evidence shipments for a component
- :doc:`docs/integrators_guide` — verify, intake, and integrate received shipments

🏢 Professional Deployment
==========================

For organizations adopting OSQAr across teams and projects:

- :doc:`docs/lifecycle_management` — requirements lifecycle, baselines, change management
- :doc:`docs/multi_project_workflows` — workspace orchestration, dependency closure, batch intake
- :doc:`docs/collaboration_workflows` — multi-user workflows, review processes, team coordination
- :doc:`docs/ci_integration` — wire OSQAr into GitHub Actions or other CI pipelines

🔧 Reference
============

- :doc:`docs/cli_reference` — full per-command reference (all flags, exit codes, examples)
- :doc:`docs/configuration_and_hooks` — project/workspace config files, custom commands, hooks
- :doc:`docs/tool_reliance_boundary` — fail-closed Clause 11 tool-reliance boundary and external-assurance separation
- :doc:`docs/evidence_acceptance` — controlled evidence states, fail-closed profiles, and limits
- :doc:`docs/iso26262_reference_catalog` — researched ISO 26262 mappings and explicit OSQAr policy boundaries
- :doc:`docs/typed_traceability` — directed qualification graph and API-to-requirement projection

📦 Examples
===========

OSQAr ships with reference examples for C, C++, Rust, and Python:

- `All examples <examples/>`_

For **safety-related embedded** projects, OSQAr recommends **C** or **Rust**. The **Python** example is an easy-to-run demo for the documentation and traceability workflow.

Full demonstration — OSQAr-cJSON
--------------------------------

For a complete, real-world qualification project, see:

- `OSQAr-cJSON <https://github.com/BitVortex/OSQAr-cJSON>`_ — an ISO 26262 SEooC qualification attempt of the cJSON library targeting ASIL D, with CI-driven evidence shipments, 88% statement coverage, 162 Unity tests, and reproducible builds.

🧠 Agent Skills
===============

OSQAr ships with content-authoring skills that help authors — human engineers and
AI agents alike — map ISO standards requirements onto OSQAr qualification needs.

- :doc:`docs/agent_skills_usage` — how agents should navigate the three-tier skill
  ecosystem (content-authoring + domain-specific + organization-specific), task
  routing, clause verification, and common pitfalls
