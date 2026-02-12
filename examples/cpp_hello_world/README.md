# OSQAr Example (C++): Temperature Monitor (TSIM)

This example mirrors the reference documentation flow, but the implementation and tests are written in **C++**.

It also links against the shared C library example in `../c_shared_lib` (used to showcase workspace dependency deduplication).

## Workflow

1) Build and run native tests (generates `test_results.xml` in JUnit format)
2) Generate a code complexity report (`complexity_report.txt` via `lizard`)
3) Build Sphinx documentation (imports `test_results.xml` via `sphinx-test-reports`)

## Quick start

```bash
cd examples/cpp_hello_world
./build-and-test.sh
open _build/html/index.html
```

## Reproducible builds (native)

The example supports a reproducible build mode for the native binary.

```bash
cd examples/cpp_hello_world
export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
OSQAR_REPRODUCIBLE=1 ./build-and-test.sh
```

This mode normalizes timestamps, locale/timezone, and compiler-embedded source paths.

## Native build only

```bash
cd examples/cpp_hello_world

# Option A: CMake (if installed)
cmake -S . -B build
cmake --build build

# Option B: plain C++ compiler
cc -O2 -I../c_shared_lib/include -c ../c_shared_lib/src/osqar_shared.c -o build/osqar_shared.o
c++ -std=c++17 -O2 -Iinclude -I../c_shared_lib/include -c src/tsim.cpp -o build/tsim.o
c++ -std=c++17 -O2 -Iinclude -I../c_shared_lib/include -c tests/test_tsim.cpp -o build/test_tsim.o
c++ -o build/junit_tests build/osqar_shared.o build/tsim.o build/test_tsim.o

./build/junit_tests test_results.xml
```

## Bazel (optional)

If you use Bazel, the example ships minimal Bazel build files:

```bash
cd examples/cpp_hello_world
bazel build //...
bazel run //:junit_tests -- test_results.xml

# Reproducible Bazel build
export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
OSQAR_REPRODUCIBLE=1 ./bazel-build-and-test.sh
```
