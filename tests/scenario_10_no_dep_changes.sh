#!/usr/bin/env bash
# Scenario 10: Non-dependency file changes only
set -euo pipefail
source "$(dirname "$0")/helpers.sh"

setup_scenario "no-dep-changes"

# Modify only a source file, not a dependency manifest
cat >> "$REPO_ROOT/test-projects/go-project/main.go" << 'EOF'
// a comment change
EOF

make_test_commit "change source file only"

BASE=$(get_base_sha)
HEAD=$(get_head_sha)

echo "--- Testing detect_changes.py ---"
run_detect "$BASE" "$HEAD"
assert_output "has_changes" "false"
assert_output "ecosystem" "none"

teardown_scenario
echo -e "${GREEN}Scenario 10 PASSED${NC}"
