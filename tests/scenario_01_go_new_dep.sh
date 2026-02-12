#!/usr/bin/env bash
# Scenario 01: Add a new Go dependency
set -euo pipefail
source "$(dirname "$0")/helpers.sh"

setup_scenario "go-new-dep"

# Add a new dependency to go.mod
cat > "$REPO_ROOT/test-projects/go-project/go.mod" << 'EOF'
module github.com/example/test-go-project

go 1.22

require (
	github.com/lib/pq v1.10.9
	golang.org/x/text v0.14.0
)
EOF

make_test_commit "add golang.org/x/text"

BASE=$(get_base_sha)
HEAD=$(get_head_sha)

echo "--- Testing go_deps.py ---"
output=$(run_go_deps "$BASE" "$HEAD")
assert_line_in "golang.org/x/text@v0.14.0" "$output"

echo "--- Testing detect_changes.py ---"
run_detect "$BASE" "$HEAD"
assert_output "has_changes" "true"
assert_output "ecosystem" "go"
assert_output_contains "dependencies" "golang.org/x/text"

teardown_scenario
echo -e "${GREEN}Scenario 01 PASSED${NC}"
