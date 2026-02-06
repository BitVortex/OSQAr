#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}OSQAr example (Rust): Build & Traceability Workflow${NC}\n"

ACTION="all"
if [[ "${1:-}" == "build" || "${1:-}" == "test" || "${1:-}" == "docs" || "${1:-}" == "all" ]]; then
  ACTION="$1"
  shift
fi

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

  export CARGO_INCREMENTAL=0
  EXTRA_RUSTFLAGS="$(osqar_rust_reproducible_flags)"
  export RUSTFLAGS="${RUSTFLAGS:-} ${EXTRA_RUSTFLAGS}"
fi

if [[ "${ACTION}" == "all" || "${ACTION}" == "build" ]]; then
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
fi

if [[ "${ACTION}" == "all" || "${ACTION}" == "test" ]]; then
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
fi

if [[ "${ACTION}" == "all" || "${ACTION}" == "test" ]]; then
  echo -e "\n${BLUE}Step 3: Code coverage report (cargo llvm-cov, best-effort)${NC}"
  rm -f coverage_report.txt coverage.xml

  if [[ "${COVERAGE}" == "1" ]] && command -v cargo >/dev/null 2>&1 && cargo llvm-cov --help >/dev/null 2>&1; then
    # Note: `cargo llvm-cov` is an optional tool. Install with:
    #   cargo install cargo-llvm-cov
    # Some environments also require: rustup component add llvm-tools-preview
    if [[ "${REPRODUCIBLE}" == "1" ]]; then
      cargo llvm-cov run --locked --release --bin junit_tests -- test_results.xml >/dev/null 2>&1 || true
      cargo llvm-cov report --locked --release --summary-only > coverage_report.txt 2>&1 || true
      cargo llvm-cov report --locked --release --cobertura --output-path coverage.xml >/dev/null 2>&1 || true
    else
      cargo llvm-cov run --bin junit_tests -- test_results.xml >/dev/null 2>&1 || true
      cargo llvm-cov report --summary-only > coverage_report.txt 2>&1 || true
      cargo llvm-cov report --cobertura --output-path coverage.xml >/dev/null 2>&1 || true
    fi
  fi

  if [ ! -f coverage_report.txt ]; then
    echo "Rust code coverage report not generated in this environment." > coverage_report.txt
    echo "Install: cargo install cargo-llvm-cov" >> coverage_report.txt
    echo "Then run: OSQAR_COVERAGE=1 ./build-and-test.sh" >> coverage_report.txt
  fi
  echo -e "${GREEN}✓ Wrote coverage_report.txt${NC}"

  echo -e "\n${BLUE}Step 4: Code complexity report${NC}"
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
      ensure_poetry_deps || true
      poetry run lizard -C 10 src > complexity_report.txt 2>&1 || true
      echo -e "${GREEN}✓ Wrote complexity_report.txt (lizard fallback)${NC}"
    fi
  fi
fi

if [[ "${ACTION}" == "all" || "${ACTION}" == "docs" ]]; then
  echo -e "\n${BLUE}Step 5: Build documentation${NC}"
  if command -v poetry >/dev/null 2>&1; then
    rm -rf _build/html
    ensure_poetry_deps
    poetry run sphinx-build -b html . _build/html 2>&1 | tail -10

    # Ship raw evidence files alongside the HTML directory (for CI shipments / audits)
    cp -f test_results.xml _build/html/test_results.xml >/dev/null 2>&1 || true
    cp -f coverage_report.txt _build/html/coverage_report.txt >/dev/null 2>&1 || true
    cp -f complexity_report.txt _build/html/complexity_report.txt >/dev/null 2>&1 || true
    if [ -f coverage.xml ]; then
      cp -f coverage.xml _build/html/coverage.xml >/dev/null 2>&1 || true
    fi

    # Ship implementation sources alongside the docs (so a bundle can be reviewed end-to-end)
    mkdir -p _build/html/implementation/src
    cp -a src/. _build/html/implementation/src/ >/dev/null 2>&1 || true
    cp -f Cargo.toml _build/html/implementation/Cargo.toml >/dev/null 2>&1 || true
    if [ -f Cargo.lock ]; then
      cp -f Cargo.lock _build/html/implementation/Cargo.lock >/dev/null 2>&1 || true
    fi
  else
    echo -e "${RED}✗ Poetry not found. Install via: pipx install poetry (or pip install poetry)${NC}"
    exit 1
  fi
fi

echo -e "\n${GREEN}✅ Done (${ACTION})${NC}"
if [[ "${ACTION}" == "all" || "${ACTION}" == "docs" ]]; then
  echo "- HTML: _build/html/index.html"
fi
if [[ "${ACTION}" == "all" || "${ACTION}" == "test" ]]; then
  echo "- JUnit: test_results.xml"
  echo "- Coverage: coverage_report.txt"
  echo "- Complexity: complexity_report.txt"
fi
