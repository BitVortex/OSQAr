#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}OSQAr example (C): Build & Traceability Workflow${NC}\n"

ensure_poetry_deps() {
  # Evidence tooling is optional; try to install it, but fall back to the lean install.
  poetry install --no-interaction --with evidence >/dev/null 2>&1 || \
    poetry install --no-interaction >/dev/null 2>&1
}

REPRODUCIBLE="${OSQAR_REPRODUCIBLE:-0}"
if [[ "${1:-}" == "--reproducible" ]]; then
  REPRODUCIBLE=1
  shift
fi

COVERAGE="${OSQAR_COVERAGE:-1}"
if [[ "${1:-}" == "--no-coverage" ]]; then
  COVERAGE=0
  shift
elif [[ "${1:-}" == "--coverage" ]]; then
  COVERAGE=1
  shift
fi

if [[ "${REPRODUCIBLE}" == "1" ]]; then
  if [[ -f "${SCRIPT_DIR}/osqar_tools/reproducible_build_env.sh" ]]; then
    # shellcheck source=/dev/null
    source "${SCRIPT_DIR}/osqar_tools/reproducible_build_env.sh"
  elif [[ -f "${SCRIPT_DIR}/../../tools/reproducible_build_env.sh" ]]; then
    # shellcheck source=/dev/null
    source "${SCRIPT_DIR}/../../tools/reproducible_build_env.sh"
  else
    echo -e "${RED}✗ Reproducible build helper not found${NC}" >&2
    exit 1
  fi
  osqar_reproducible_setup "${SCRIPT_DIR}"

  EXTRA_CFLAGS="$(osqar_cc_reproducible_flags)"
  EXTRA_LDFLAGS="$(osqar_ld_reproducible_flags)"

  export CFLAGS="${CFLAGS:-} ${EXTRA_CFLAGS}"
  export LDFLAGS="${LDFLAGS:-} ${EXTRA_LDFLAGS}"
fi

echo -e "${BLUE}Step 1: Build native code${NC}"
if [[ "${REPRODUCIBLE}" == "1" ]]; then
  rm -rf build
fi
mkdir -p build

if command -v cmake >/dev/null 2>&1; then
  if [[ "${COVERAGE}" == "1" ]]; then
    cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug -DOSQAR_COVERAGE=ON >/dev/null
  else
    cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DOSQAR_COVERAGE=OFF >/dev/null
  fi
  cmake --build build >/dev/null
  echo -e "${GREEN}✓ Native build succeeded (CMake)${NC}"
else
  if command -v cc >/dev/null 2>&1; then
    # Use env flags if present (including reproducible flags).
    if [[ "${COVERAGE}" == "1" ]]; then
      cc -std=c11 -O0 -g -Iinclude --coverage ${CFLAGS:-} ${LDFLAGS:-} -o build/junit_tests tests/test_tsim.c src/tsim.c
    else
      cc -std=c11 -O2 -g0 -Iinclude ${CFLAGS:-} ${LDFLAGS:-} -o build/junit_tests tests/test_tsim.c src/tsim.c
    fi
    echo -e "${GREEN}✓ Native build succeeded (cc)${NC}"
  else
    echo -e "${RED}✗ Neither cmake nor cc found; cannot build native code${NC}"
    exit 1
  fi
fi

echo -e "\n${BLUE}Step 2: Run native tests (JUnit XML)${NC}"
./build/junit_tests test_results.xml
if [ -f test_results.xml ]; then
  echo -e "${GREEN}✓ Wrote test_results.xml${NC}"
else
  echo -e "${RED}✗ test_results.xml not generated${NC}"
  exit 1
fi

echo -e "\n${BLUE}Step 3: Code coverage report (gcovr, best-effort)${NC}"
rm -f coverage_report.txt coverage.xml
if [[ "${COVERAGE}" == "1" ]] && command -v poetry >/dev/null 2>&1; then
  ensure_poetry_deps || true
  if poetry run python -c "import gcovr" >/dev/null 2>&1; then
    # Text summary (embedded in docs)
    poetry run gcovr -r . --object-directory build --exclude 'tests/.*' --print-summary > coverage_report.txt 2>&1 || true
    # Cobertura XML (useful for CI tooling)
    poetry run gcovr -r . --object-directory build --exclude 'tests/.*' --xml-pretty -o coverage.xml >/dev/null 2>&1 || true
  else
    echo "gcovr not installed in the Poetry environment." > coverage_report.txt
    echo "Install: poetry install --with evidence" >> coverage_report.txt
  fi
else
  echo "Code coverage collection disabled or unavailable." > coverage_report.txt
  echo "To enable: OSQAR_COVERAGE=1 ./build-and-test.sh" >> coverage_report.txt
fi
if [ -f coverage_report.txt ]; then
  echo -e "${GREEN}✓ Wrote coverage_report.txt${NC}"
fi

echo -e "\n${BLUE}Step 4: Code complexity report (lizard)${NC}"
rm -f complexity_report.txt
if command -v poetry >/dev/null 2>&1; then
  ensure_poetry_deps || true
  # Cyclomatic complexity report (best-effort; does not fail the build)
  if poetry run python -c "import lizard" >/dev/null 2>&1; then
    poetry run lizard -C 10 src include tests > complexity_report.txt 2>&1 || true
  else
    echo "lizard not installed in the Poetry environment." > complexity_report.txt
    echo "Install: poetry install --with evidence" >> complexity_report.txt
  fi
  if [ -f complexity_report.txt ]; then
    echo -e "${GREEN}✓ Wrote complexity_report.txt${NC}"
  else
    echo -e "${RED}✗ complexity_report.txt not generated${NC}"
  fi
else
  echo -e "${RED}✗ Poetry not found; skipping complexity report${NC}"
fi

echo -e "\n${BLUE}Step 5: Build documentation${NC}"
if command -v poetry >/dev/null 2>&1; then
  rm -rf _build/html
  ensure_poetry_deps
  poetry run sphinx-build -b html . _build/html 2>&1 | tail -10

  # Ship raw evidence files alongside the HTML directory (for CI shipments / audits)
  cp -f test_results.xml _build/html/test_results.xml >/dev/null 2>&1 || true
  cp -f coverage_report.txt _build/html/coverage_report.txt >/dev/null 2>&1 || true
  if [ -f coverage.xml ]; then
    cp -f coverage.xml _build/html/coverage.xml >/dev/null 2>&1 || true
  fi

  # Ship implementation + tests alongside the docs (so a bundle can be reviewed end-to-end)
  mkdir -p _build/html/implementation/src _build/html/tests
  cp -a src/. _build/html/implementation/src/ >/dev/null 2>&1 || true
  if [ -d include ]; then
    mkdir -p _build/html/implementation/include
    cp -a include/. _build/html/implementation/include/ >/dev/null 2>&1 || true
  fi
  cp -a tests/. _build/html/tests/ >/dev/null 2>&1 || true
  cp -f CMakeLists.txt _build/html/implementation/CMakeLists.txt >/dev/null 2>&1 || true
else
  echo -e "${RED}✗ Poetry not found. Install via: pipx install poetry (or pip install poetry)${NC}"
  exit 1
fi

echo -e "\n${GREEN}✅ Done${NC}"
echo "- HTML: _build/html/index.html"
echo "- JUnit: test_results.xml"
echo "- Coverage: coverage_report.txt"
echo "- Complexity: complexity_report.txt"
