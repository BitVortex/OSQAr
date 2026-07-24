Typed qualification traceability
================================

The default ``basic`` traceability mode remains prefix-based and compatible
with existing projects. ``--profile qualification`` selects the versioned,
directed graph policy packaged as ``traceability-qualification-v1.json``.

Authoring model
---------------

Qualification projects declare relations in their authored direction. Sphinx-
Needs derives reverse navigation; authors do not duplicate reciprocal edges.
The controlled relation options are ``allocated_to``, ``allocated_to_api``,
``realized_by``, ``verified_by``, ``produces``, ``evidenced_by``,
``supported_by``, ``references``, ``constrains``, and ``applies_to``.

For example:

.. code-block:: rst

   .. need:: Parse input
      :id: REQ_PARSE
      :allocated_to: ARCH_PARSER
      :verified_by: VER_PARSE

   .. arch:: Parser architecture
      :id: ARCH_PARSER
      :realized_by: API_PARSE

   .. api:: parse()
      :id: API_PARSE
      :kind: api

A reverse link such as architecture-to-requirement does not satisfy the
requirement's ``allocated_to`` rule. Qualification mode rejects wrong source or
target types, unknown relations, dead links, duplicate IDs, unsatisfied minimum
cardinalities, and planned, superseded, or unapproved evidence used to support a
claim. Requirements, architecture, implementation, and verification nodes that
participate in the qualification lifecycle must have ``status: active``.
Qualification acceptance also requires an independently supplied source
revision and configuration SHA-256 accepted by ``osqar framework validate``;
local status strings alone are not evidence acceptance.

API-to-requirement allocation artifact
--------------------------------------

Generate the optional user-facing allocation view with:

.. code-block:: console

   osqar traceability _build/html/needs.json \
     --profile qualification \
     --json-report _build/html/typed-traceability.json \
     --api-requirements-output _build/html/api-requirements.csv

The projection begins at each API and traverses the authoritative graph in
reverse:

``API <-realized_by- architecture <-allocated_to- requirement``

It also recognizes an explicit ``requirement --allocated_to_api--> API`` edge.
Implementation IDs with ``API_`` or ``IMPL_`` prefixes are APIs by default,
even without ``kind: api``. Repeat ``--api-prefix`` to replace those defaults
with project-specific prefixes.
The CSV deliberately omits architecture columns for readability, deduplicates
requirements reached by both paths, and emits explicit ``unallocated`` rows.
The same command writes ``api-requirements.audit.json`` alongside the CSV. The
audit file records every direct or architecture-mediated path, including all
intermediate node IDs and relation names. The graph is validated before either
artifact is written. No synthetic API-to-requirement evidence edge is
introduced.

Assurance boundary
------------------

The vocabulary and cardinalities are OSQAr project policy, not graph
cardinalities prescribed by ISO 26262. Passing proves that the declared graph
satisfies this mechanical policy. It does not establish semantic adequacy,
functional-safety compliance, qualification, certification, or safety.
