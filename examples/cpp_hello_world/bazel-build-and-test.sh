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

  read -r -a CC_FLAGS <<<"$(osqar_cc_reproducible_flags)"
  for f in "${CC_FLAGS[@]}"; do
    BAZEL_ARGS+=("--copt=${f}" "--cxxopt=${f}")
  done

  read -r -a LD_FLAGS <<<"$(osqar_ld_reproducible_flags)"
  for f in "${LD_FLAGS[@]}"; do
    [[ -n "${f}" ]] && BAZEL_ARGS+=("--linkopt=${f}")
  done

  bazel clean --expunge >/dev/null 2>&1 || true
fi

bazel build //... "${BAZEL_ARGS[@]}"
JUNIT_OUT="${SCRIPT_DIR}/test_results.xml"
rm -f "${JUNIT_OUT}"
bazel run //:junit_tests "${BAZEL_ARGS[@]}" -- "${JUNIT_OUT}"

echo "✓ Bazel build completed"
echo "- JUnit: ${JUNIT_OUT}"
