# OSQAr Example (C): Temperature Monitor (TSIM)

This example mirrors the Python `hello_world` documentation flow, but the implementation and tests are written in **C**.

## Workflow

1) Build and run native tests (generates `test_results.xml` in JUnit format)
2) Generate a code complexity report (`complexity_report.txt` via `lizard`)
3) Build Sphinx documentation (imports `test_results.xml` via `sphinx-test-reports`)

### Quick start

```bash
cd examples/c_hello_world
./build-and-test.sh
open _build/html/index.html
```

### Native build only

```bash
cd examples/c_hello_world

# Option A: CMake (if installed)
cmake -S . -B build
cmake --build build

# Option B: plain C compiler
cc -std=c11 -O2 -Iinclude -o build/junit_tests tests/test_tsim.c src/tsim.c

./build/junit_tests test_results.xml
```
