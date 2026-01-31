#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}OSQAr example (Rust): Build & Traceability Workflow${NC}\n"

echo -e "${BLUE}Step 1: Build native code${NC}"
if command -v cargo >/dev/null 2>&1; then
  cargo build >/dev/null
  echo -e "${GREEN}✓ Native build succeeded (cargo)${NC}"
else
  echo -e "${RED}✗ cargo not found; install Rust via rustup${NC}"
  exit 1
fi

echo -e "\n${BLUE}Step 2: Run native tests (JUnit XML)${NC}"
cargo run --quiet --bin junit_tests -- test_results.xml
if [ -f test_results.xml ]; then
  echo -e "${GREEN}✓ Wrote test_results.xml${NC}"
else
  echo -e "${RED}✗ test_results.xml not generated${NC}"
  exit 1
fi

echo -e "\n${BLUE}Step 3: Build documentation${NC}"
if command -v poetry >/dev/null 2>&1; then
  poetry install --no-interaction >/dev/null
  poetry run sphinx-build -b html . _build/html 2>&1 | tail -10
else
  echo -e "${RED}✗ Poetry not found. Install via: pipx install poetry (or pip install poetry)${NC}"
  exit 1
fi

echo -e "\n${GREEN}✅ Done${NC}"
echo "- HTML: _build/html/index.html"
echo "- JUnit: test_results.xml"
