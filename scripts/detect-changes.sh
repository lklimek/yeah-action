#!/usr/bin/env bash
set -euo pipefail

# detect-changes.sh
#
# Main dependency change detection script for the Dependency Security Review
# GitHub Action. Operates in two modes:
#
# 1. Force mode: When INPUT_DEPENDENCY is set, bypasses auto-detection and
#    infers the ecosystem from the dependency name.
#
# 2. Auto-detection mode: Diffs the PR to find changed dependency manifest
#    files (go.mod, go.sum, Cargo.toml, Cargo.lock) and extracts the specific
#    dependencies that changed.
#
# Outputs (written to GITHUB_OUTPUT):
#   ecosystem    - "go", "rust", "mixed", or "none"
#   dependencies - comma-separated list of changed dependencies
#   has_changes  - "true" or "false"

# ---------------------------------------------------------------------------
# Helper: write a key=value pair to GITHUB_OUTPUT.
# ---------------------------------------------------------------------------
set_output() {
  local key="${1}"
  local value="${2}"
  echo "${key}=${value}" >> "${GITHUB_OUTPUT}"
}

# ---------------------------------------------------------------------------
# Force mode: INPUT_DEPENDENCY is provided, skip auto-detection.
# ---------------------------------------------------------------------------
if [[ -n "${INPUT_DEPENDENCY:-}" ]]; then
  echo "Force mode: dependency explicitly provided as '${INPUT_DEPENDENCY}'"

  # Determine ecosystem: explicit override > inference from name.
  ecosystem=""

  if [[ -n "${INPUT_ECOSYSTEM:-}" ]]; then
    # Explicit ecosystem override provided.
    ecosystem="${INPUT_ECOSYSTEM}"
  elif [[ "${INPUT_DEPENDENCY}" =~ ^[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}/ ]]; then
    # Looks like a Go module path (starts with a domain: github.com/, golang.org/, etc.).
    ecosystem="go"
  elif [[ -f "Cargo.toml" ]] || find . -maxdepth 3 -name "Cargo.toml" -print -quit 2>/dev/null | grep -q .; then
    # No domain-like prefix, but a Cargo.toml exists somewhere in the workspace.
    ecosystem="rust"
  else
    # Default fallback.
    ecosystem="go"
  fi

  echo "Inferred ecosystem: ${ecosystem}"

  set_output "has_changes" "true"
  set_output "ecosystem" "${ecosystem}"
  set_output "dependencies" "${INPUT_DEPENDENCY}"
  exit 0
fi

# ---------------------------------------------------------------------------
# Auto-detection mode: examine the PR diff to find dependency file changes.
# ---------------------------------------------------------------------------
echo "Auto-detection mode: scanning PR diff for dependency changes"

# Validate that required environment variables are set.
: "${BASE_SHA:?BASE_SHA environment variable is required}"
: "${HEAD_SHA:?HEAD_SHA environment variable is required}"
: "${ACTION_PATH:?ACTION_PATH environment variable is required}"

# Get the list of files changed in the PR.
changed_files="$(git diff --name-only "${BASE_SHA}...${HEAD_SHA}" 2>/dev/null || true)"

if [[ -z "${changed_files}" ]]; then
  echo "No changed files detected between ${BASE_SHA} and ${HEAD_SHA}"
  set_output "has_changes" "false"
  set_output "ecosystem" "none"
  set_output "dependencies" ""
  exit 0
fi

echo "Changed files:"
echo "${changed_files}"

# Check for Go dependency files (go.mod, go.sum in any subdirectory).
has_go=false
if echo "${changed_files}" | grep -qE '(^|/)go\.(mod|sum)$'; then
  has_go=true
  echo "Detected Go dependency file changes"
fi

# Check for Rust dependency files (Cargo.toml, Cargo.lock in any subdirectory).
has_rust=false
if echo "${changed_files}" | grep -qE '(^|/)Cargo\.(toml|lock)$'; then
  has_rust=true
  echo "Detected Rust dependency file changes"
fi

# If no dependency files changed, exit early.
if [[ "${has_go}" == "false" && "${has_rust}" == "false" ]]; then
  echo "No dependency manifest files changed in this PR"
  set_output "has_changes" "false"
  set_output "ecosystem" "none"
  set_output "dependencies" ""
  exit 0
fi

# ---------------------------------------------------------------------------
# Extract changed dependencies from each detected ecosystem.
# ---------------------------------------------------------------------------
go_deps=""
rust_deps=""

if [[ "${has_go}" == "true" ]]; then
  echo "Extracting Go dependency changes..."
  # Source the Go dependency extraction function.
  # shellcheck source=go-deps.sh
  source "${ACTION_PATH}/scripts/go-deps.sh"
  go_deps="$(extract_go_deps "${BASE_SHA}" "${HEAD_SHA}" || true)"
  if [[ -n "${go_deps}" ]]; then
    echo "Go dependencies changed:"
    echo "${go_deps}"
  else
    echo "Go manifest files changed but no individual dependency changes detected"
  fi
fi

if [[ "${has_rust}" == "true" ]]; then
  echo "Extracting Rust dependency changes..."
  # Source the Rust dependency extraction function.
  # shellcheck source=rust-deps.sh
  source "${ACTION_PATH}/scripts/rust-deps.sh"
  rust_deps="$(extract_rust_deps "${BASE_SHA}" "${HEAD_SHA}" || true)"
  if [[ -n "${rust_deps}" ]]; then
    echo "Rust dependencies changed:"
    echo "${rust_deps}"
  else
    echo "Rust manifest files changed but no individual dependency changes detected"
  fi
fi

# ---------------------------------------------------------------------------
# Determine ecosystem label and combine dependency lists.
# ---------------------------------------------------------------------------
if [[ "${has_go}" == "true" && "${has_rust}" == "true" ]]; then
  ecosystem="mixed"
elif [[ "${has_go}" == "true" ]]; then
  ecosystem="go"
else
  ecosystem="rust"
fi

# Combine all detected dependencies into a single newline-separated list,
# then convert to comma-separated for the output.
all_deps=""
if [[ -n "${go_deps}" ]]; then
  all_deps="${go_deps}"
fi
if [[ -n "${rust_deps}" ]]; then
  if [[ -n "${all_deps}" ]]; then
    all_deps="${all_deps}"$'\n'"${rust_deps}"
  else
    all_deps="${rust_deps}"
  fi
fi

# Convert newline-separated list to comma-separated.
dependencies=""
if [[ -n "${all_deps}" ]]; then
  dependencies="$(echo "${all_deps}" | paste -sd ',' -)"
fi

# Determine if there are actual dependency changes to review.
if [[ -n "${dependencies}" ]]; then
  has_changes="true"
else
  # Manifest files changed but we could not extract specific dependencies.
  # Still flag as changed so the review step can inspect the diff.
  has_changes="true"
fi

echo ""
echo "Summary:"
echo "  ecosystem:    ${ecosystem}"
echo "  dependencies: ${dependencies}"
echo "  has_changes:  ${has_changes}"

set_output "has_changes" "${has_changes}"
set_output "ecosystem" "${ecosystem}"
set_output "dependencies" "${dependencies}"
