#!/usr/bin/env bash
# Scenario 11: Force mode with Go module path (ecosystem inferred)
set -euo pipefail
source "$(dirname "$0")/helpers.sh"

setup_scenario "force-go"

export INPUT_DEPENDENCY="github.com/lib/pq"
unset INPUT_ECOSYSTEM 2>/dev/null || true

echo "--- Testing detect_changes.py (force mode) ---"
# Force mode doesn't need real commits, but needs GITHUB_OUTPUT
python3 "$SCRIPTS_DIR/detect_changes.py"

assert_output "has_changes" "true"
assert_output "ecosystem" "go"
assert_output "dependencies" "github.com/lib/pq"

unset INPUT_DEPENDENCY

teardown_scenario
echo -e "${GREEN}Scenario 11 PASSED${NC}"
