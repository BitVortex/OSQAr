# ASIL target example for Rust

This generated project is an **incomplete example** of an OSQAr evidence model
for a Rust library targeting ASIL D. It demonstrates exemplary links among
standards claims, draft project needs, source, planned verification, and pending
evidence. It does **not** establish ASIL qualification, compliance,
certification, or safety.

## Prerequisites

OSQAr does not install a Rust toolchain. Confirm that Rust and Cargo are
available with `rustc --version` and `cargo --version`. Availability does not
establish suitability for your project.

## Try it

```bash
./build-and-test.sh test
osqar build-docs
osqar traceability _build/html/needs.json \
  --project-config osqar_project.json \
  --json-report _build/html/traceability_report.json
```

The traceability command is expected to return nonzero in the untouched
example: several draft requirements deliberately lack architecture links. Use
the reported violations as a tailoring queue; do not relabel them as accepted.

Then inspect:

- `00_standards_claims.rst` for bounded example interpretations;
- `01_requirements.rst` through `06_lifecycle_management.rst` for linked needs;
- `src/lib.rs` for a small checked-arithmetic implementation; and
- `05_test_results.rst` for explicitly pending evidence placeholders.

Before project use, replace or remove every example claim, select an authorized
catalog, tailor the requirements and acceptance criteria, pin the Rust toolchain,
and capture real evidence through the project's review process.
