#!/usr/bin/env bash
# Scenario 03: Multiple Go dependency changes (upgrade + new deps)
set -euo pipefail
source "$(dirname "$0")/helpers.sh"

setup_scenario "go-multi-deps"

cat > "$REPO_ROOT/test-projects/go-project/go.mod" << 'EOF'
module github.com/example/test-go-project

go 1.22

require (
	github.com/lib/pq v1.10.10
	golang.org/x/text v0.14.0
	golang.org/x/net v0.21.0
)
EOF

make_test_commit "multi dep changes"

BASE=$(get_base_sha)
HEAD=$(get_head_sha)

echo "--- Testing go_deps.py ---"
output=$(run_go_deps "$BASE" "$HEAD")
assert_line_in "github.com/lib/pq@v1.10.9..v1.10.10" "$output"
assert_line_in "golang.org/x/text@v0.14.0" "$output"
assert_line_in "golang.org/x/net@v0.21.0" "$output"

echo "--- Testing detect_changes.py ---"
run_detect "$BASE" "$HEAD"
assert_output "has_changes" "true"
assert_output "ecosystem" "go"
assert_output_contains "dependencies" "lib/pq"
assert_output_contains "dependencies" "x/text"
assert_output_contains "dependencies" "x/net"

teardown_scenario
echo -e "${GREEN}Scenario 03 PASSED${NC}"
