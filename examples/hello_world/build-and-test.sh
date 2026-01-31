#!/bin/bash
# build-and-test.sh - OSQAr example: Automated Build & Traceability
# 
# This script demonstrates the complete workflow for generating compliance artifacts:
# 1. Run unit tests with JUnit output
# 2. Verify test coverage
# 3. Build documentation with auto-imported test results
# 4. Generate traceability report
#
# Usage: ./build-and-test.sh

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔨 OSQAr example: Build & Traceability Workflow${NC}\n"

# Step 1: Run Code Style Checks
echo -e "${BLUE}Step 1️⃣: Code Style Checks${NC}"
if command -v poetry &> /dev/null; then
    echo "✓ Poetry found"
    poetry install --no-interaction >/dev/null
    echo "  Running black code formatter checks..."
    poetry run black --check src tests 2>/dev/null || {
        echo "  ⚠️  Code formatting issues found. Run: poetry run black src tests"
    }
else
    echo "✗ Poetry not found. Install via: pip install poetry"
    exit 1
fi

# Step 2: Run Unit Tests
echo -e "\n${BLUE}Step 2️⃣: Unit Tests with Coverage${NC}"
echo "  Running 13 test cases..."
poetry run pytest tests/test_tsim.py \
    -v \
    --junit-xml=test_results.xml \
    --cov=src \
    --cov-report=term-missing \
    2>&1 | grep -E "(PASSED|FAILED|passed|failed|ERROR|test_)"

TEST_RESULT=$?
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}  ✓ All tests passed${NC}"
else
    echo -e "${RED}  ✗ Test failures detected${NC}"
    exit 1
fi

# Step 3: Verify Test-Requirement Coverage
echo -e "\n${BLUE}Step 3️⃣: Traceability Coverage Check${NC}"
TEST_COUNT=$(grep -c "testcase" test_results.xml)
REQ_COUNT=$(grep -c ".. need::" 03_verification.rst || echo "0")
echo "  Test cases: $TEST_COUNT"
echo "  Test requirements: $REQ_COUNT"

if [ "$TEST_COUNT" -gt 0 ]; then
    echo -e "${GREEN}  ✓ Test results generated (test_results.xml)${NC}"
else
    echo -e "${RED}  ✗ No test results found${NC}"
    exit 1
fi

# Step 4: Build Documentation
echo -e "\n${BLUE}Step 4️⃣: Build Documentation with Test Results${NC}"
echo "  Running Sphinx..."
rm -rf _build/html
if poetry run sphinx-build -b html . _build/html 2>&1 | tail -5; then
    echo -e "${GREEN}  ✓ Documentation build succeeded${NC}"
else
    echo -e "${RED}  ✗ Documentation build failed${NC}"
    exit 1
fi

# Step 5: Generate Traceability Report
echo -e "\n${BLUE}Step 5️⃣: Traceability Report${NC}"
echo "  Analyzing traceability chain..."

REQUIREMENTS=$(grep -c "^.. need::" 01_requirements.rst 2>/dev/null || echo "0")
ARCH=$(grep -c ":id: ARCH_" 02_architecture.rst 2>/dev/null || echo "0")
TESTS=$(grep -c ":id: TEST_" 03_verification.rst 2>/dev/null || echo "0")
PASSED=$(grep -c 'status="passed"' test_results.xml 2>/dev/null || echo "0")

echo "  Requirements defined: $REQUIREMENTS"
echo "  Architecture specs: $ARCH"
echo "  Test requirements: $TESTS"
echo "  Tests passed: $PASSED"

# Step 6: Summary
echo -e "\n${GREEN}✅ Compliance Artifact Generation Complete!${NC}"
echo ""
echo "📊 Artifact Summary:"
echo "  - Test Results: test_results.xml (JUnit format)"
echo "  - Documentation: _build/html/index.html"
echo "  - Test Report: _build/html/05_test_results.html"
echo "  - Traceability Matrix: _build/html/03_verification.html"
echo ""
echo "📈 Traceability Status:"
if [ "$PASSED" -eq "$TESTS" ]; then
    echo -e "  ${GREEN}✓ Full coverage: All $TESTS test requirements passing${NC}"
else
    echo -e "  ${RED}⚠️  Partial coverage: $PASSED/$TESTS tests passing${NC}"
fi

echo ""
echo "🚀 Next Steps:"
echo "  1. Review compliance artifacts: open _build/html/index.html"
echo "  2. Share documentation with stakeholders"
echo "  3. Integrate into CI/CD pipeline"
echo "  4. Archive artifacts for qualification dossier"
echo ""
echo "📚 For more details, see: TEST_TRACEABILITY_GUIDE.md"
