#!/usr/bin/env bash
# Scenario 04: Transitive dependency changes via go.sum (no go.mod change)
set -euo pipefail
source "$(dirname "$0")/helpers.sh"

setup_scenario "go-gosum"

# Create a go.sum with a transitive dep
cat > "$REPO_ROOT/test-projects/go-project/go.sum" << 'EOF'
github.com/lib/pq v1.10.9 h1:abc123=
golang.org/x/crypto v0.18.0 h1:def456=
EOF

make_test_commit "add go.sum with transitive dep"

BASE=$(get_base_sha)
HEAD=$(get_head_sha)

echo "--- Testing go_deps.py ---"
output=$(run_go_deps "$BASE" "$HEAD")
assert_line_in "golang.org/x/crypto" "$output"

echo "--- Testing detect_changes.py ---"
run_detect "$BASE" "$HEAD"
assert_output "has_changes" "true"
assert_output "ecosystem" "go"
assert_output_contains "dependencies" "golang.org/x/crypto"

# Clean up go.sum
rm -f "$REPO_ROOT/test-projects/go-project/go.sum"

teardown_scenario
echo -e "${GREEN}Scenario 04 PASSED${NC}"
