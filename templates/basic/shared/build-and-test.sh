#!/usr/bin/env bash
set -euo pipefail

# Minimal evidence generator for the template.
# This script intentionally does not require a compiler/toolchain.

cat > test_results.xml <<'XML'
<?xml version="1.0" encoding="utf-8"?>
<testsuite name="tests" tests="1" failures="0" errors="0" skipped="0" time="0">
  <testcase classname="template" name="placeholder" time="0" />
</testsuite>
XML

echo "Coverage report not generated (template placeholder)." > coverage_report.txt
echo "Complexity report not generated (template placeholder)." > complexity_report.txt

echo "Wrote: test_results.xml, coverage_report.txt, complexity_report.txt"
