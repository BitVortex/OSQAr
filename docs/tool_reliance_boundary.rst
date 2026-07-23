Safety-tool reliance boundary
=============================

Status and standards basis
--------------------------

ISO 26262-8:2018 Clause 11 was confirmed against the controlled copy as the
context for confidence in the use of software tools. This OSQAr reliance strategy
is still a **project interpretation**, not a standard-prescribed classification.

No OSQAr function is currently permitted for safety-lifecycle reliance by this
base strategy. The packaged inventory
``osqar_data/governance/tool-reliance-v1.json`` deliberately sets
``reliance_permitted`` to ``false`` for every function and leaves version
applicability unresolved. This is fail-closed: implementation, tests, or
community use alone cannot activate a reliance claim.

The strategy does not assert that OSQAr, a generated component, or any work
product is qualified, compliant, certified, or safe.

Claim boundary
--------------

A future organization- or user-level assurance disposition may permit reliance
only on explicitly named, machine-checkable predicates for an exact OSQAr
version, profile version, configuration, dependency set, and supported
environment. Such permission
would mean only that the documented predicate may support the identified
lifecycle decision within its operating constraints.

It would not establish:

* correctness or completeness of requirements;
* adequacy of allocations or verification methods;
* sufficiency of evidence;
* validity of assumptions of use or deviations;
* completeness of impact analysis;
* soundness of a safety argument;
* signer authority or organizational trust;
* component or tool qualification;
* ISO 26262 conformity.

Candidate mechanical predicates
--------------------------------

The inventory identifies these candidates, all currently disabled:

* checksum verification of declared bytes;
* exact release-manifest inventory and integrity verification;
* directed typed-traceability validation;
* mechanical evidence-state and provenance validation;
* detached-signature cryptographic verification;
* strict shipment aggregation of separately named predicates.

Each candidate is provisionally treated as capable of failing to detect an
error in a relied-upon lifecycle work product. The packaged TI, tool-error-
detection, and TCL labels are provisional research classifications, not final
ISO 26262-8:2018 Clause 11 determinations. The adopting organization must
establish or replace them for its exact use case using controlled standard text.

Functions outside the boundary
------------------------------

The following remain convenience aids or explicitly excluded functions:

* build and test orchestration until completion/report acceptance is separately
  justified;
* impact traversal;
* baseline diff reports;
* GSN generation;
* workspace combination;
* project scaffolding, diagnostics, metadata, and reporting.

Their outputs may inform competent assessment. They must not replace complete
impact analysis, lifecycle assessment, evidence assessment, or safety-argument
judgment.

Required per-function argument
------------------------------

The base inventory cannot be changed to ``reliance_permitted: true``. An
organization or user that intends to rely on a function must maintain a
separate assurance record identifying:

#. the exact downstream decision allowed to rely on the result;
#. the input, output, configuration, exclusions, and operating constraints;
#. every material erroneous output and whether it introduces or fails to
   detect a lifecycle-work-product error;
#. the use-case-specific Tool Impact rationale;
#. the independent detection mechanisms and their demonstrated strength;
#. the resulting tool-confidence disposition;
#. exact OSQAr, profile, Python, dependency, and platform versions;
#. immutable validation evidence;
#. known anomalies and residual limitations;
#. the accountable authorization and its supporting assessment record.

The base inventory validator rejects any attempt to set
``reliance_permitted`` to ``true``. It validates the shipped structural and
technical boundary only; organization- and user-level assessment logs,
authorizations, and reliance decisions remain outside the base framework.

Required independent evidence
-----------------------------

Evidence should be selected per predicate. The minimum candidate set is:

* hand-authored positive and negative fixtures with independent expected
  results;
* fault-seeded missing, extra, corrupted, stale, duplicated, reversed,
  malformed, skipped, unavailable, and zero-test cases where applicable;
* differential checksum or signature verification using a separate
  implementation;
* an independently implemented typed-graph oracle;
* destination rehash and source-to-destination inventory reconciliation;
* source-tree and clean installed-wheel execution;
* deterministic machine-readable reports;
* captured command, OSQAr version, profile version, Python/dependency versions,
  configuration, exclusions, hooks, and platform;
* an independently assessed validation report tied to an immutable revision.

Reusing the same OSQAr implementation to generate and verify an artifact is
not automatically independent error detection. The argument must state the
specific fault detected by each external measure.

Dependencies and coupled failures
---------------------------------

The use-case assessment must include relevant dependencies and external tools,
including Sphinx, Sphinx-Needs, report parsers, YAML/JSON libraries, packaging
and build tooling, cryptographic tools, and external test/build commands.
An internally consistent ``needs.json`` can still be wrong because of an
upstream transformation defect. The disposition must either control that
failure mode or state it as a limitation.

Anomalies and revalidation
--------------------------

A relied-upon version requires a known-anomaly register recording affected
functions, versions, impact, workaround, detection status, and whether prior
outputs require regeneration.

Revalidation assessment is required after changes to at least:

* the behavior profile or acceptance policy;
* traceability vocabulary or cardinalities;
* report parsers and result-state handling;
* checksum, path, exclusion, or release-inventory semantics;
* signature handling or trust configuration;
* supported dependencies, Python versions, or operating platforms;
* a known anomaly affecting a relied-upon predicate.

Organization- and user-level assurance records
----------------------------------------------

The base framework deliberately contains no assessor identity, assessment log,
or authorization status. Adopting organizations and users maintain those
records under their own governance. Such records should establish, per function
and exact use case, the downstream decision, Tool Impact rationale, independent
detection strength, exact environment and configuration, immutable evidence,
semantic boundaries, coupled dependency failures, anomalies, accountable
authority, and authorization outcome.

An external authorization is per function and use case. It is not blanket
approval of OSQAr and must not be represented by modifying the shipped base
inventory.
