Safety-tool reliance boundary
=============================

Status and standards basis
--------------------------

This strategy is a **researched interpretation** of ISO 26262-8:2018,
Clause 11. It has not yet been checked against a controlled copy of the
standard. ``BitVortex`` is the designated independent functional-safety
reviewer.

No OSQAr function is currently approved for safety-lifecycle reliance by this
strategy. The packaged inventory
``osqar_data/governance/tool-reliance-v1.json`` deliberately sets
``reliance_permitted`` to ``false`` for every function and leaves version
applicability unresolved. This is fail-closed: implementation, tests, or
community use alone cannot activate a reliance claim.

The strategy does not assert that OSQAr, a generated component, or any work
product is qualified, compliant, certified, or safe.

Claim boundary
--------------

A future reviewed disposition may permit reliance only on explicitly named,
machine-checkable predicates for an exact OSQAr version, profile version,
configuration, dependency set, and supported environment. Such permission
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
Clause 11 determinations. ``BitVortex`` must confirm or replace them using the
exact use case and controlled standard.

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

Their outputs may inform competent review. They must not replace complete
impact analysis, lifecycle review, evidence assessment, or safety-argument
judgment.

Required per-function argument
------------------------------

Before changing a function to ``reliance_permitted: true``, its inventory
record and supporting report shall identify:

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
#. independent approval by the designated reviewer.

The inventory validator rejects reliance unless all documented controls are
machine-resolved: exact OSQAr, profile, Python, dependency, configuration, and
environment applicability; controlled-copy-reviewed standards status; a named
lifecycle decision and owner; nonblank independent detection; immutable
evidence; explicit assumptions, constraints, limitations, anomalies, and
revalidation triggers; and approval by the fixed designated reviewer
``BitVortex``. Immutable evidence entries bind a 40- or 64-hex revision into the
identifier, bind the evidence digest through ``urn:sha256:<digest>``, and name a
relative local JSON evidence artifact. Validation hashes the artifact bytes and
requires its evidence-envelope revision to equal the declared revision.
Placeholder, whitespace-only, or unresolved values fail closed.

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
* an independently reviewed validation report tied to an immutable revision.

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

Revalidation review is required after changes to at least:

* the behavior profile or acceptance policy;
* traceability vocabulary or cardinalities;
* report parsers and result-state handling;
* checksum, path, exclusion, or release-inventory semantics;
* signature handling or trust configuration;
* supported dependencies, Python versions, or operating platforms;
* a known anomaly affecting a relied-upon predicate.

Independent review gate
-----------------------

``BitVortex`` should answer, for every candidate function:

#. Is the downstream lifecycle decision stated precisely?
#. Is the Tool Impact rationale use-case-specific?
#. Could a warning, skipped step, exclusion, missing tool, stale report, or
   empty test suite still yield a pass?
#. Is the claimed detection mechanism independent of the implementation being
   assessed?
#. Are exact versions, dependencies, configuration, and operating limits
   fixed?
#. Do the evidence identifiers resolve to immutable, reproducible results?
#. Are semantic judgments visibly outside the automated claim?
#. Are coupled dependency failures and anomalies addressed?

Only after those questions are resolved against controlled standard text and
versioned evidence may the inventory status become ``reviewed`` and an
individual candidate become permitted. Approval is per function and use case;
it is not blanket approval of OSQAr.
