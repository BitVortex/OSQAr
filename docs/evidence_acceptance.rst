Evidence states and acceptance
==============================

OSQAr distinguishes authoring plans, executed results, artifact state, and
mechanical acceptance. Generating or packaging a report does not approve it.

Profiles
--------

``basic`` preserves the documentation-first workflow. Its validation result
contains ``acceptance_claimed: false`` and must not be presented as qualification
evidence acceptance.

``qualification`` is fail-closed. Required activities pass only when all of the
following are true:

* activity state is ``completed``;
* result state is ``passed`` or ``passed-with-deviation``;
* evidence state is ``approved`` and is not ``superseded``;
* applicability is explicit;
* source revision, configuration identity/hash, command, tool name/version, and
  environment are recorded;
* activity source/configuration values exactly match the project declarations;
* the project declarations exactly match trusted ``--source-revision`` and
  ``--configuration-sha256`` values supplied by the reviewing caller;
* ``required`` values are JSON booleans, not truthy/falsy substitutes;
* the activity history begins at ``planned``, contains known states, follows
  every permitted transition, and ends at the declared current state;
* the project-relative report exists, is non-empty, and matches its SHA-256;
* JUnit XML has a JUnit root, at least one executed test, recursively consistent
  suite/testcase counters, and zero failures, errors, or skips;
* configured thresholds pass;
* findings are closed or have an approved deviation;
* required gaps are not open.

Controlled states
-----------------

Activity states are ``planned``, ``ready``, ``running``, ``completed``,
``failed``, and ``waived``. Allowed transitions are versioned in
``osqar_data/profiles/qualification.yaml``. A completed or waived activity may
not silently return to an execution state.

Result states are ``not-run``, ``invalid``, ``failed``, ``passed``, and
``passed-with-deviation``. Evidence states are ``missing``, ``generated``,
``validated``, ``approved``, and ``superseded``. Gap states are ``open``,
``approved``, and ``closed``.

An approved deviation requires a named reviewer and rationale. It records a
review disposition; it does not turn a failed criterion into an ordinary pass.

Command
-------

.. code-block:: console

   osqar framework validate \
     --project osqar_project.json \
     --profile qualification \
     --source-revision "$REVIEWED_GIT_COMMIT" \
     --configuration-sha256 "$REVIEWED_CONFIGURATION_SHA256" \
     --report-json _evidence/framework-acceptance.json

Exit status is zero only when the selected profile passes. For
``qualification``, the source and configuration values are independent trust
anchors: derive them from the reviewed commit and controlled configuration,
not from the project file being checked. Omitting either anchor fails closed.
The JSON report uses schema ``osqar.acceptance-report.v1``. A requested report
target is invalidated before validation and published through an atomic
replacement; an I/O failure returns status 2, cleanup failures are contained,
and any regular temporary that cannot be removed is neutralized so stale
successful acceptance evidence cannot survive.

Boundary
--------

This validator checks declared state, provenance, hashes, thresholds, and
review dispositions. It does not determine whether requirements are correct,
whether evidence is technically sufficient, or whether a safety argument is
convincing. Passing does not establish ISO 26262 compliance, tool qualification,
component qualification, certification, or safety.

Standards-claim validation boundary
-----------------------------------

``STDCLAIM_*`` needs add a separate mechanical check to traceability. The check
confirms that each authored catalog and ``reference_id`` resolves and that the
claim's typed links have the permitted direction and resolve to project needs.
A mechanical PASS does **not** approve the project interpretation, determine
applicability, establish evidence adequacy, or demonstrate conformance or
compliance with any standard. Those determinations require project-authorized
human review against the controlled source and project context.

The base boilerplate deliberately carries no organization-specific approval,
acceptance, waiver, or applicability disposition. An adopting organization must
record its own named reviewer, scope, rationale, date, and controlled revision in
its external governance or review record. Such a disposition must not be
inferred from an example claim, a generated reverse link, or a zero CLI exit
status.

Likewise, an ``evidenced_by`` relationship records only the authored direction
from a claim to an ``EVID_*`` record. A placeholder or pending evidence record
does not assert execution, a passing result, provenance, technical sufficiency,
review, or acceptance. Promote evidence through the controlled evidence states
only after those facts and dispositions exist; catalog resolution alone cannot
perform that promotion.
