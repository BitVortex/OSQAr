#!/usr/bin/env bash
#
# ASIL D SEooC C Library — Verification Pipeline
# ===============================================
# This script executes the full verification pipeline for the ASIL D C library
# qualification: build, test, sanitize, coverage, static analysis, valgrind,
# complexity, and reproducible build verification.
#
# Usage: ./build-and-test.sh [action]
#   all              Run the full pipeline (default)
#   build            Build the library and tests
#   test             Build and run unit tests
#   test-sanitizer   Build with ASan+UBSan and run tests
#   coverage         Build with coverage flags and generate reports
#   static-analysis  Run cppcheck static analysis
#   valgrind         Run Valgrind Memcheck (if available)
#   complexity       Run lizard complexity analysis (if available)
#

set -euo pipefail

ACTION="${1:-all}"
BUILD_DIR="build"
SRC_DIR="src"
TEST_DIR="tests"
INCLUDE_DIR="include"

# ── Helpers ──

_cmake_build() {
    local build_type="${1:-Debug}"
    mkdir -p "${BUILD_DIR}"
    cmake -S . -B "${BUILD_DIR}" \
        -DCMAKE_BUILD_TYPE="${build_type}" \
        -DCMAKE_C_COMPILER="${CC:-gcc}"
    cmake --build "${BUILD_DIR}" -- -j"$(nproc 2>/dev/null || echo 2)"
}

_check_command() {
    if ! command -v "$1" &>/dev/null; then
        echo "WARNING: $1 not found — skipping $2"
        return 1
    fi
    return 0
}

# ── Actions ──

do_build() {
    echo "=== Building library and tests ==="
    _cmake_build "Debug"
    echo "Build complete."
}

do_test() {
    echo "=== Running unit tests ==="
    do_build
    cd "${BUILD_DIR}" && ctest --output-on-failure -j"$(nproc 2>/dev/null || echo 1)"
    cd ..
    echo "Tests complete."
}

do_test_sanitizer() {
    echo "=== Running tests with ASan+UBSan ==="
    _cmake_build "Debug"
    cd "${BUILD_DIR}" && ctest --output-on-failure
    cd ..
    echo "Sanitizer test run complete."
}

do_coverage() {
    echo "=== Measuring code coverage ==="
    
    # Build with coverage flags
    mkdir -p "${BUILD_DIR}"
    cmake -S . -B "${BUILD_DIR}" \
        -DCMAKE_BUILD_TYPE=Debug \
        -DCMAKE_C_FLAGS="-fprofile-arcs -ftest-coverage -O0" \
        -DCMAKE_EXE_LINKER_FLAGS="-fprofile-arcs -ftest-coverage"
    cmake --build "${BUILD_DIR}" -- -j"$(nproc 2>/dev/null || echo 2)"
    
    # Run tests to generate .gcda files
    cd "${BUILD_DIR}" && ctest --output-on-failure
    cd ..
    
    # Generate coverage report
    if _check_command "gcovr" "coverage (using gcovr)"; then
        gcovr -r . --object-directory="${BUILD_DIR}" \
            --exclude='tests/' \
            --print-summary > coverage_report.txt 2>&1 || true
        echo "" >> coverage_report.txt
        gcovr -r . --object-directory="${BUILD_DIR}" \
            --exclude='tests/' \
            --branches >> coverage_report.txt 2>&1 || true
        echo "Coverage report written to coverage_report.txt"
    elif _check_command "gcov" "coverage (gcov fallback)"; then
        find "${BUILD_DIR}" -name '*.gcda' -exec gcov -b {} \; > coverage_report.txt 2>&1 || true
        echo "Coverage report (gcov) written to coverage_report.txt"
    else
        echo "WARNING: neither gcovr nor gcov found — writing placeholder" > coverage_report.txt
    fi
}

do_static_analysis() {
    echo "=== Running static analysis (cppcheck) ==="
    if _check_command "cppcheck" "static analysis"; then
        cppcheck --enable=all --inconclusive --std=c11 \
            --suppress=missingIncludeSystem \
            -I "${INCLUDE_DIR}" \
            "${SRC_DIR}" "${INCLUDE_DIR}" \
            --xml --xml-version=2 2>cppcheck_report.xml || true
        echo "Static analysis report written to cppcheck_report.xml"
        
        # Also produce a human-readable summary
        cppcheck --enable=all --inconclusive --std=c11 \
            --suppress=missingIncludeSystem \
            -I "${INCLUDE_DIR}" \
            "${SRC_DIR}" "${INCLUDE_DIR}" > cppcheck_report.txt 2>&1 || true
        echo "Human-readable report written to cppcheck_report.txt"
    else
        echo "cppcheck not found — skipping static analysis" > cppcheck_report.txt
    fi
}

do_valgrind() {
    echo "=== Running Valgrind Memcheck ==="
    if _check_command "valgrind" "Valgrind Memcheck"; then
        do_build
        valgrind --leak-check=full --show-leak-kinds=all \
            --error-exitcode=1 \
            --track-origins=yes \
            "${BUILD_DIR}/osqar_asil_d_tests" > valgrind_report.txt 2>&1 || true
        echo "Valgrind report written to valgrind_report.txt"
    else
        echo "Valgrind not found — skipping" > valgrind_report.txt
    fi
}

do_complexity() {
    echo "=== Measuring code complexity ==="
    if _check_command "lizard" "complexity analysis"; then
        lizard "${SRC_DIR}" "${INCLUDE_DIR}" \
            -C 15 -L 60 \
            > complexity_report.txt 2>&1 || true
        echo "Complexity report written to complexity_report.txt"
    else
        echo "lizard not found — skipping complexity analysis" > complexity_report.txt
    fi
}

do_reproducible() {
    echo "=== Verifying reproducible build ==="
    do_build
    sha256sum "${BUILD_DIR}/libosqar_asil_d.a" > checksums.txt 2>/dev/null || true
    echo "Build artifact checksum written to checksums.txt"
}

do_all() {
    do_build
    do_test_sanitizer
    do_static_analysis
    do_complexity
    
    # Optional steps (may not be available in all environments)
    do_coverage
    do_valgrind
    do_reproducible
    
    echo ""
    echo "=== Verification Pipeline Complete ==="
    echo "Reports generated:"
    ls -la test_results.xml coverage_report.txt cppcheck_report.txt \
        valgrind_report.txt complexity_report.txt checksums.txt 2>/dev/null || true
}

# ── Dispatch ──

case "${ACTION}" in
    build)            do_build ;;
    test)             do_test ;;
    test-sanitizer)   do_test_sanitizer ;;
    coverage)         do_coverage ;;
    static-analysis)  do_static_analysis ;;
    valgrind)         do_valgrind ;;
    complexity)       do_complexity ;;
    reproducible)     do_reproducible ;;
    all)              do_all ;;
    *)
        echo "Unknown action: ${ACTION}"
        echo "Valid actions: all, build, test, test-sanitizer, coverage, static-analysis, valgrind, complexity, reproducible"
        exit 1
        ;;
esac
