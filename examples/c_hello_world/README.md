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

### Reproducible builds (native)

The example supports a reproducible build mode for the native binary.

```bash
cd examples/c_hello_world
export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
OSQAR_REPRODUCIBLE=1 ./build-and-test.sh
```

This mode normalizes timestamps, locale/timezone, and compiler-embedded source paths.

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

### Bazel (optional)

If you use Bazel, the example ships minimal Bazel build files:

```bash
cd examples/c_hello_world
bazel build //...
bazel run //:junit_tests -- test_results.xml

# Reproducible Bazel build
export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
OSQAR_REPRODUCIBLE=1 ./bazel-build-and-test.sh
```
