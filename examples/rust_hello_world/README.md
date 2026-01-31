# OSQAr Example (Rust): Temperature Monitor (TSIM)

This example mirrors the reference documentation flow, but the implementation and tests are written in **Rust**.

## Workflow

1) Build and run native tests (generates `test_results.xml` in JUnit format)
2) Generate a code complexity report (`complexity_report.txt` via `cargo-cyclo` or a `lizard` fallback)
3) Build Sphinx documentation (imports `test_results.xml` via `sphinx-test-reports`)

## Quick start

```bash
cd examples/rust_hello_world
./build-and-test.sh
open _build/html/index.html
```

## Native build only

```bash
cd examples/rust_hello_world

cargo build
cargo run --bin junit_tests -- test_results.xml
```
