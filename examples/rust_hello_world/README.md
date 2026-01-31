# OSQAr Example (Rust): Temperature Monitor (TSIM)

This example mirrors the reference documentation flow, but the implementation and tests are written in **Rust**.

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
