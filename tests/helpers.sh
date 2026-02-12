#!/usr/bin/env bash
# tests/helpers.sh — Common setup/teardown/assertions for scenario tests.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$REPO_ROOT/scripts"
ORIGINAL_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"
TEST_BRANCH=""
GITHUB_OUTPUT_FILE=""

# ---------- colours ---------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ---------- setup / teardown ------------------------------------------------
setup_scenario() {
    local scenario_name="${1:?scenario name required}"
    TEST_BRANCH="test/${scenario_name}-$$"
    GITHUB_OUTPUT_FILE="$(mktemp)"
    export GITHUB_OUTPUT="$GITHUB_OUTPUT_FILE"
    export ACTION_PATH="$REPO_ROOT"

    echo -e "${YELLOW}Setting up: ${scenario_name}${NC}"

    # Create a new branch from current HEAD
    git -C "$REPO_ROOT" checkout -b "$TEST_BRANCH" --quiet
}

make_test_commit() {
    local msg="${1:-test commit}"
    # IMPORTANT: Only stage test-projects/ — NOT -A, which would stage
    # the test scripts themselves and break teardown.
    git -C "$REPO_ROOT" add test-projects/
    git -C "$REPO_ROOT" commit -m "$msg" --quiet --allow-empty
}

get_base_sha() {
    # Return the commit before the test commit (parent of HEAD)
    git -C "$REPO_ROOT" rev-parse HEAD~1
}

get_head_sha() {
    git -C "$REPO_ROOT" rev-parse HEAD
}

teardown_scenario() {
    echo -e "${YELLOW}Tearing down...${NC}"
    # Switch back to original branch
    git -C "$REPO_ROOT" checkout "$ORIGINAL_BRANCH" --force --quiet
    # Delete the test branch
    git -C "$REPO_ROOT" branch -D "$TEST_BRANCH" --quiet 2>/dev/null || true
    # Clean up temp file
    rm -f "$GITHUB_OUTPUT_FILE"
}

# ---------- runners ---------------------------------------------------------
run_detect() {
    # Run detect_changes.py with BASE_SHA and HEAD_SHA
    export BASE_SHA="${1:?base_sha required}"
    export HEAD_SHA="${2:?head_sha required}"
    python3 "$SCRIPTS_DIR/detect_changes.py"
}

run_go_deps() {
    python3 "$SCRIPTS_DIR/go_deps.py" "${1:?base_sha}" "${2:?head_sha}"
}

run_rust_deps() {
    python3 "$SCRIPTS_DIR/rust_deps.py" "${1:?base_sha}" "${2:?head_sha}"
}

# ---------- assertions ------------------------------------------------------
get_output() {
    # Get a specific key from GITHUB_OUTPUT
    local key="$1"
    grep "^${key}=" "$GITHUB_OUTPUT_FILE" | head -1 | cut -d= -f2-
}

assert_output() {
    local key="$1"
    local expected="$2"
    local actual
    actual="$(get_output "$key")"
    if [[ "$actual" == "$expected" ]]; then
        echo -e "  ${GREEN}PASS${NC}: ${key} = '${actual}'"
        return 0
    else
        echo -e "  ${RED}FAIL${NC}: ${key} expected '${expected}', got '${actual}'"
        return 1
    fi
}

assert_output_contains() {
    local key="$1"
    local substring="$2"
    local actual
    actual="$(get_output "$key")"
    if [[ "$actual" == *"$substring"* ]]; then
        echo -e "  ${GREEN}PASS${NC}: ${key} contains '${substring}'"
        return 0
    else
        echo -e "  ${RED}FAIL${NC}: ${key} does not contain '${substring}' (got '${actual}')"
        return 1
    fi
}

assert_output_not_empty() {
    local key="$1"
    local actual
    actual="$(get_output "$key")"
    if [[ -n "$actual" ]]; then
        echo -e "  ${GREEN}PASS${NC}: ${key} is not empty (='${actual}')"
        return 0
    else
        echo -e "  ${RED}FAIL${NC}: ${key} is empty"
        return 1
    fi
}

assert_line_in() {
    # Assert that stdout output (piped in) contains a line matching a pattern.
    local pattern="$1"
    local output="$2"
    if echo "$output" | grep -qF "$pattern"; then
        echo -e "  ${GREEN}PASS${NC}: output contains '${pattern}'"
        return 0
    else
        echo -e "  ${RED}FAIL${NC}: output does not contain '${pattern}'"
        echo "  Output was: $output"
        return 1
    fi
}

assert_empty() {
    local label="$1"
    local value="$2"
    if [[ -z "$value" ]]; then
        echo -e "  ${GREEN}PASS${NC}: ${label} is empty"
        return 0
    else
        echo -e "  ${RED}FAIL${NC}: ${label} should be empty but got '${value}'"
        return 1
    fi
}
