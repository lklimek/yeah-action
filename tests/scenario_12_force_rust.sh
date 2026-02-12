#!/usr/bin/env bash
# Scenario 12: Force mode with Rust crate (inferred from Cargo.toml presence)
set -euo pipefail
source "$(dirname "$0")/helpers.sh"

setup_scenario "force-rust"

export INPUT_DEPENDENCY="tokio"
unset INPUT_ECOSYSTEM 2>/dev/null || true

echo "--- Testing detect_changes.py (force mode) ---"
python3 "$SCRIPTS_DIR/detect_changes.py"

assert_output "has_changes" "true"
assert_output "ecosystem" "rust"
assert_output "dependencies" "tokio"

unset INPUT_DEPENDENCY

teardown_scenario
echo -e "${GREEN}Scenario 12 PASSED${NC}"
