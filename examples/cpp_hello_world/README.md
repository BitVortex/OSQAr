# OSQAr Example (C++): Temperature Monitor (TSIM)

This example mirrors the reference documentation flow, but the implementation and tests are written in **C++**.

## Quick start

```bash
cd examples/cpp_hello_world
./build-and-test.sh
open _build/html/index.html
```

## Native build only

```bash
cd examples/cpp_hello_world

# Option A: CMake (if installed)
cmake -S . -B build
cmake --build build

# Option B: plain C++ compiler
c++ -std=c++17 -O2 -Iinclude -o build/junit_tests tests/test_tsim.cpp src/tsim.cpp

./build/junit_tests test_results.xml
```
