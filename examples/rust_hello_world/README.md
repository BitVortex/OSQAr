# OSQAr Example (Rust): Temperature Monitor (TSIM)

This example mirrors the reference documentation flow, but the implementation and tests are written in **Rust**.

It also links against the shared C library example in `../c_shared_lib` (used to showcase workspace dependency deduplication). A C compiler is required.

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

## Reproducible builds (native)

The example supports a reproducible build mode for the native binary.

```bash
cd examples/rust_hello_world
export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
OSQAR_REPRODUCIBLE=1 ./build-and-test.sh
```

This mode normalizes timestamps, locale/timezone, disables incremental compilation, and remaps embedded source paths.

## Native build only

```bash
cd examples/rust_hello_world

cargo build
cargo run --bin junit_tests -- test_results.xml
```

## Bazel (optional)

If you use Bazel, the example ships minimal Bazel build files:

```bash
cd examples/rust_hello_world
bazel build //...
bazel run //:junit_tests -- test_results.xml

# Reproducible Bazel build
export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
OSQAR_REPRODUCIBLE=1 ./bazel-build-and-test.sh
```
