#!/usr/bin/env bash
# Scenario 02: Upgrade an existing Go dependency
set -euo pipefail
source "$(dirname "$0")/helpers.sh"

setup_scenario "go-upgrade-dep"

# Upgrade lib/pq from v1.10.9 to v1.10.10
cat > "$REPO_ROOT/test-projects/go-project/go.mod" << 'EOF'
module github.com/example/test-go-project

go 1.22

require github.com/lib/pq v1.10.10
EOF

make_test_commit "upgrade lib/pq"

BASE=$(get_base_sha)
HEAD=$(get_head_sha)

echo "--- Testing go_deps.py ---"
output=$(run_go_deps "$BASE" "$HEAD")
assert_line_in "github.com/lib/pq@v1.10.9..v1.10.10" "$output"

echo "--- Testing detect_changes.py ---"
run_detect "$BASE" "$HEAD"
assert_output "has_changes" "true"
assert_output "ecosystem" "go"
assert_output_contains "dependencies" "github.com/lib/pq"

teardown_scenario
echo -e "${GREEN}Scenario 02 PASSED${NC}"
