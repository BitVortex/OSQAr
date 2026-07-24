Closed release manifests
========================

A checksum manifest proves only the files it lists. Release-manifest
verification additionally requires inventory closure: every regular
file must be declared or match an explicit reported exclusion.

Listed-file compatibility mode
------------------------------

Existing projects retain listed-file verification:

.. code-block:: console

   osqar checksum verify --root _shipment --manifest _shipment/SHA256SUMS

Add ``--closed-set`` to reject unlisted regular files. The manifest itself and
explicit ``--exclude`` patterns are omitted from the compared inventory. JSON
reports state whether closed-set mode was used and list unexpected files.

Versioned release contract
--------------------------

For a prepared release shipment, generate the JSON contract:

.. code-block:: console

   osqar release-manifest generate \
     --root _shipment \
     --output _shipment/OSQAR-RELEASE-MANIFEST.json \
     --release-version v0.10.0 \
     --source-revision "$GIT_COMMIT" \
     --producer-command "osqar shipment prepare --project ." \
     --tool-version 0.9.0 \
     --description-output release-description.md

The manifest schema is ``osqar.release-manifest.v1``. It binds each required
artifact to its relative path, size, SHA-256, producer command, source revision,
and OSQAr version. Exclusions are explicit data.

An authored entry may instead set ``required`` to ``false``. Its absence is
reported separately and does not fail verification. If present, its size and
digest must still match, and undeclared extra files remain failures.

The final outer release manifest explicitly excludes only itself because a
manifest cannot contain its own digest without circularity. Every other
downloadable asset, including ``SHA256SUMS``, detached signature material, and
materialized provenance, is included in the closed inventory.

Verify with:

.. code-block:: console

   osqar release-manifest verify \
     --root _shipment \
     --manifest _shipment/OSQAR-RELEASE-MANIFEST.json \
     --release-version v0.10.0 \
     --source-revision "$GIT_COMMIT" \
     --report-json release-verification.json

Verification rejects malformed or duplicate records, an empty artifact inventory,
missing, stale, empty, or unexpected artifacts, and invalid paths or hashes.
Repeated exclusion patterns are normalized to one entry so generated manifests
remain deterministic and conform to the schema. The optional Markdown release
description is generated from the same manifest inventory to prevent hand-written
asset lists from diverging.

Generate only after the shipment directory has reached its final boundary.
The release manifest is deliberately outside its own payload list; this avoids
self-reference. Inner ``SHA256SUMS`` files remain ordinary listed payloads and
retain their existing shipment-level meaning. Verification should pin both the
expected release version and immutable source revision. Exclusions are explicit
glob patterns in the manifest and must be reviewed as part of the release.

Boundary
--------

Closed-set verification establishes artifact-set completeness relative to the
manifest plus byte integrity. It does not establish authenticity unless the
manifest is separately signed, and it does not establish semantic adequacy,
functional-safety compliance, qualification, certification, or safety.
