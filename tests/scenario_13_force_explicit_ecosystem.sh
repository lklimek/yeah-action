#!/usr/bin/env bash
# Scenario 13: Force mode with explicit ecosystem override
set -euo pipefail
source "$(dirname "$0")/helpers.sh"

setup_scenario "force-explicit-ecosystem"

export INPUT_DEPENDENCY="my-custom-crate"
export INPUT_ECOSYSTEM="rust"

echo "--- Testing detect_changes.py (force mode, explicit ecosystem) ---"
python3 "$SCRIPTS_DIR/detect_changes.py"

assert_output "has_changes" "true"
assert_output "ecosystem" "rust"
assert_output "dependencies" "my-custom-crate"

unset INPUT_DEPENDENCY
unset INPUT_ECOSYSTEM

teardown_scenario
echo -e "${GREEN}Scenario 13 PASSED${NC}"
