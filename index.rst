OSQAr — Open Safety Qualification Architecture
==============================================

OSQAr helps teams author, check, package, and exchange auditable engineering
evidence. It connects human-readable requirements and architecture to explicit
traceability, verification records, implementation, and integrity-protected
shipments.

OSQAr performs versioned mechanical checks. A successful result does not decide
that a system is safe, compliant, certified, or qualified, and does not replace
project-specific engineering judgment or independent assessment.

Start here
==========

New to OSQAr? Follow these pages in order:

#. :doc:`docs/getting_started` — install the CLI and build a first project.
#. :doc:`docs/using_the_boilerplate` — understand project, shipment, and
   workspace concepts and follow the day-to-day workflow.
#. :doc:`docs/asil_examples` — explore the C and Rust ASIL-target examples while
   keeping the target distinct from achieved qualification.
#. :doc:`docs/project_setup_from_scratch` — create a production project or
   migrate existing engineering content.

.. toctree::
   :maxdepth: 2
   :caption: Start here

   docs/getting_started
   docs/using_the_boilerplate
   docs/asil_examples
   docs/project_setup_from_scratch

Task guides
===========

Choose the guide that matches your immediate job:

* :doc:`docs/suppliers_guide` — author, check, and ship component evidence.
* :doc:`docs/integrators_guide` — verify, intake, and preserve received evidence.
* :doc:`docs/ci_integration` — automate checks and generated artifacts.
* :doc:`docs/lifecycle_management` — manage baselines and controlled changes.
* :doc:`docs/multi_project_workflows` — verify dependencies and workspaces.
* :doc:`docs/collaboration_workflows` — coordinate authors and reviewers.

.. toctree::
   :maxdepth: 1
   :caption: Task guides

   docs/suppliers_guide
   docs/integrators_guide
   docs/ci_integration
   docs/lifecycle_management
   docs/multi_project_workflows
   docs/collaboration_workflows

Power-user reference
====================

Use these pages when you need exact behavior, configuration, or assurance
boundaries:

* :doc:`docs/cli_reference` — commands, options, outputs, and exit behavior.
* :doc:`docs/configuration_and_hooks` — project/workspace configuration and hooks.
* :doc:`docs/evidence_acceptance` — controlled evidence states and validation.
* :doc:`docs/typed_traceability` — strict directed profiles and API projection.
* :doc:`docs/tool_reliance_boundary` — mechanical checks versus tool assurance.
* :doc:`docs/release_manifest` — closed release-payload validation.
* :doc:`docs/iso26262_reference_catalog` — researched mappings and explicit
  project-policy boundaries.
* :doc:`docs/agent_skills_usage` — content-authoring support for agents and
  human reviewers.

.. toctree::
   :maxdepth: 1
   :caption: Power-user reference

   docs/cli_reference
   docs/configuration_and_hooks
   docs/evidence_acceptance
   docs/typed_traceability
   docs/tool_reliance_boundary
   docs/release_manifest
   docs/iso26262_reference_catalog
   docs/agent_skills_usage

Reference projects
==================

The repository contains basic examples for C, C++, Python, and Rust. The CLI
also packages two deliberately incomplete ASIL-target examples:
``asil_example_c`` and ``asil_example_rust``. See :doc:`docs/asil_examples`
before adapting either one.

.. toctree::
   :maxdepth: 1
   :caption: Repository examples

   examples/index

For a larger external demonstration, see `OSQAr-cJSON
<https://github.com/BitVortex/OSQAr-cJSON>`_. It is a qualification attempt
targeting ASIL D, not evidence that qualification has been achieved.
