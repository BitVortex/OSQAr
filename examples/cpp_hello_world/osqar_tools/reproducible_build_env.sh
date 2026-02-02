#!/usr/bin/env bash
# OSQAr helper to make native builds more reproducible.
#
# This file is intentionally vendored into example templates so that
# projects scaffolded from the examples remain self-contained.

set -euo pipefail

osqar_reproducible_setup() {
  local source_root
  source_root="${1:-$PWD}"

  export TZ="UTC"
  export LANG="C"
  export LC_ALL="C"

  if [[ -z "${SOURCE_DATE_EPOCH:-}" ]]; then
    if command -v git >/dev/null 2>&1 && [[ -d "${source_root}/.git" ]]; then
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

  export OSQAR_SOURCE_ROOT="${source_root}"
}

osqar_cc_reproducible_flags() {
  local root="${OSQAR_SOURCE_ROOT:-$PWD}"
  printf '%s' "-ffile-prefix-map=${root}=. -fdebug-prefix-map=${root}=. -Wdate-time"
}

osqar_ld_reproducible_flags() {
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
  printf '%s' "--remap-path-prefix=${root}=."
}
