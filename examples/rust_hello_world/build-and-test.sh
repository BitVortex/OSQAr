#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}OSQAr example (Rust): Build & Traceability Workflow${NC}\n"

REPRODUCIBLE="${OSQAR_REPRODUCIBLE:-0}"
if [[ "${1:-}" == "--reproducible" ]]; then
  REPRODUCIBLE=1
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

  export CARGO_INCREMENTAL=0
  EXTRA_RUSTFLAGS="$(osqar_rust_reproducible_flags)"
  export RUSTFLAGS="${RUSTFLAGS:-} ${EXTRA_RUSTFLAGS}"
fi

echo -e "${BLUE}Step 1: Build native code${NC}"
if command -v cargo >/dev/null 2>&1; then
  if [[ "${REPRODUCIBLE}" == "1" ]]; then
    cargo clean >/dev/null 2>&1 || true
    cargo build --locked --release >/dev/null
  else
    cargo build >/dev/null
  fi
  echo -e "${GREEN}✓ Native build succeeded (cargo)${NC}"
else
  echo -e "${RED}✗ cargo not found; install Rust via rustup${NC}"
  exit 1
fi

echo -e "\n${BLUE}Step 2: Run native tests (JUnit XML)${NC}"
if [[ "${REPRODUCIBLE}" == "1" ]]; then
  cargo run --quiet --locked --release --bin junit_tests -- test_results.xml
else
  cargo run --quiet --bin junit_tests -- test_results.xml
fi
if [ -f test_results.xml ]; then
  echo -e "${GREEN}✓ Wrote test_results.xml${NC}"
else
  echo -e "${RED}✗ test_results.xml not generated${NC}"
  exit 1
fi

echo -e "\n${BLUE}Step 3: Code complexity report${NC}"
rm -f complexity_report.txt

if command -v cargo-cyclo >/dev/null 2>&1; then
  cargo cyclo > complexity_report.txt 2>&1 || true
  echo -e "${GREEN}✓ Wrote complexity_report.txt (cargo-cyclo)${NC}"
elif command -v cargo >/dev/null 2>&1 && cargo cyclo --help >/dev/null 2>&1; then
  cargo cyclo > complexity_report.txt 2>&1 || true
  echo -e "${GREEN}✓ Wrote complexity_report.txt (cargo cyclo)${NC}"
else
  echo -e "${BLUE}i${NC} cargo-cyclo not installed; skipping Rust-specific complexity report"
  echo "  Install with: cargo install cargo-cyclo"

  # Optional: lizard can still provide a basic report for Rust sources.
  if command -v poetry >/dev/null 2>&1; then
    poetry run lizard -C 10 src > complexity_report.txt 2>&1 || true
    echo -e "${GREEN}✓ Wrote complexity_report.txt (lizard fallback)${NC}"
  fi
fi

echo -e "\n${BLUE}Step 4: Build documentation${NC}"
if command -v poetry >/dev/null 2>&1; then
  rm -rf _build/html
  poetry install --no-interaction >/dev/null
  poetry run sphinx-build -b html . _build/html 2>&1 | tail -10
else
  echo -e "${RED}✗ Poetry not found. Install via: pipx install poetry (or pip install poetry)${NC}"
  exit 1
fi

echo -e "\n${GREEN}✅ Done${NC}"
echo "- HTML: _build/html/index.html"
echo "- JUnit: test_results.xml"
echo "- Complexity: complexity_report.txt"
