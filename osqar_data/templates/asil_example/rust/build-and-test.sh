#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-all}"

build() {
    cargo build --all-targets
}

test_project() {
    cargo test --all-targets
}

static_analysis() {
    cargo clippy --all-targets -- -D warnings
}

case "${ACTION}" in
    build) build ;;
    test) test_project ;;
    static-analysis) static_analysis ;;
    all)
        build
        test_project
        static_analysis
        ;;
    *)
        echo "Unknown action: ${ACTION}" >&2
        echo "Valid actions: all, build, test, static-analysis" >&2
        exit 2
        ;;
esac

cat <<'EOF'
Verification commands completed. The documentation evidence records remain
pending until project-controlled result, provenance, and review artifacts are
created and accepted; this script does not assert qualification.
EOF
