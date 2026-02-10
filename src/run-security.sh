#!/usr/bin/env bash
set -euo pipefail

RESULTS_DIR="$1"

ensure_tool() {
  local check_cmd="$1"
  local install_cmd="$2"
  if ! eval "$check_cmd" >/dev/null 2>&1; then
    eval "$install_cmd"
  fi
}

if [ "${INPUT_CARGO_AUDIT:-true}" = "true" ]; then
  echo "Running cargo audit..."
  ensure_tool "cargo audit --version" "cargo install cargo-audit --locked"
  cargo audit --json > "$RESULTS_DIR/audit.json" 2>&1 || true
fi

if [ "${INPUT_CARGO_DENY:-true}" = "true" ]; then
  echo "Running cargo deny..."
  ensure_tool "cargo deny --version" "cargo install cargo-deny --locked"
  cargo deny check 2>&1 | tee "$RESULTS_DIR/deny.txt" || true
fi

if [ "${INPUT_CARGO_VET:-true}" = "true" ]; then
  echo "Running cargo vet..."
  ensure_tool "cargo vet --version" "cargo install cargo-vet --locked"
  cargo vet --output-format=json > "$RESULTS_DIR/vet.json" 2>&1 || true
fi

if [ "${INPUT_CARGO_GEIGER:-true}" = "true" ]; then
  echo "Running cargo geiger..."
  ensure_tool "cargo geiger --version" "cargo install cargo-geiger --locked"
  cargo geiger --output-format json --quiet > "$RESULTS_DIR/geiger.json" 2>&1 || true
fi
