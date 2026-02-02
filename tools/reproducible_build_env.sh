#!/usr/bin/env bash
# Shared helper to make native builds more reproducible.
#
# Usage (from an example directory):
#   source ../../tools/reproducible_build_env.sh
#   osqar_reproducible_setup "$PWD"
#
# The caller is responsible for applying CFLAGS/CXXFLAGS/RUSTFLAGS, etc.

set -euo pipefail

osqar_reproducible_setup() {
  local source_root
  source_root="${1:-$PWD}"

  # Normalize the environment.
  export TZ="UTC"
  export LANG="C"
  export LC_ALL="C"

  # SOURCE_DATE_EPOCH is the de-facto standard for reproducible timestamps.
  # Prefer a stable value derived from the latest git commit.
  if [[ -z "${SOURCE_DATE_EPOCH:-}" ]]; then
    if command -v git >/dev/null 2>&1 && [[ -d "${source_root}/.git" ]]; then
      # Latest commit timestamp (seconds since epoch).
      SOURCE_DATE_EPOCH="$(git -C "${source_root}" log -1 --format=%ct 2>/dev/null || true)"
      if [[ -n "${SOURCE_DATE_EPOCH}" ]]; then
        export SOURCE_DATE_EPOCH
      fi
    fi
  fi

  if [[ -z "${SOURCE_DATE_EPOCH:-}" ]]; then
    echo "WARNING: SOURCE_DATE_EPOCH not set and git timestamp unavailable." >&2
    echo "         Set SOURCE_DATE_EPOCH to get deterministic timestamps." >&2
  fi

  # Remember the absolute root to allow consistent remapping.
  export OSQAR_SOURCE_ROOT="${source_root}"
}

osqar_cc_reproducible_flags() {
  local root="${OSQAR_SOURCE_ROOT:-$PWD}"
  # -ffile-prefix-map: normalizes file paths embedded into debug info.
  # -fdebug-prefix-map: supported by GCC/Clang, similar effect.
  # -Wdate-time: warns on __DATE__/__TIME__ usage (good hygiene for determinism).
  printf '%s' "-ffile-prefix-map=${root}=. -fdebug-prefix-map=${root}=. -Wdate-time"
}

osqar_ld_reproducible_flags() {
  # Build IDs can introduce nondeterminism (especially on ELF).
  # On macOS, these flags are not applicable.
  case "$(uname -s)" in
    Linux)
      printf '%s' "-Wl,--build-id=none"
      ;;
    *)
      printf '%s' ""
      ;;
  esac
}

osqar_rust_reproducible_flags() {
  local root="${OSQAR_SOURCE_ROOT:-$PWD}"
  # Remap absolute paths out of compiler diagnostics and debug info.
  # Disable incremental compilation to reduce nondeterminism.
  printf '%s' "--remap-path-prefix=${root}=."
}
