#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

REPRODUCIBLE="${OSQAR_REPRODUCIBLE:-0}"
if [[ "${1:-}" == "--reproducible" ]]; then
  REPRODUCIBLE=1
  shift
fi

BAZEL_ARGS=("--config=reproducible")

if [[ "${REPRODUCIBLE}" == "1" ]]; then
  # shellcheck source=/dev/null
  source "${SCRIPT_DIR}/osqar_tools/reproducible_build_env.sh"
  osqar_reproducible_setup "${SCRIPT_DIR}"

  # Best-effort: prefer an optimized build and a clean rebuild.
  BAZEL_ARGS+=("-c" "opt")
  bazel clean --expunge >/dev/null 2>&1 || true
fi

bazel build //... "${BAZEL_ARGS[@]}"

# Run the test binary to emit JUnit XML (kept in repo root for the example docs).
bazel run //:junit_tests "${BAZEL_ARGS[@]}" -- test_results.xml

echo "✓ Bazel build completed"
echo "- JUnit: test_results.xml"
