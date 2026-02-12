#!/usr/bin/env bash
# Scenario 07: Transitive dependency changes via Cargo.lock
set -euo pipefail
source "$(dirname "$0")/helpers.sh"

setup_scenario "rust-lock"

# Create a Cargo.lock with transitive deps
cat > "$REPO_ROOT/test-projects/rust-project/Cargo.lock" << 'EOF'
[[package]]
name = "test-rust-project"
version = "0.1.0"

[[package]]
name = "serde"
version = "1.0.197"

[[package]]
name = "syn"
version = "2.0.50"
EOF

make_test_commit "add Cargo.lock with transitive deps"

BASE=$(get_base_sha)
HEAD=$(get_head_sha)

echo "--- Testing rust_deps.py ---"
output=$(run_rust_deps "$BASE" "$HEAD")
assert_line_in "syn@2.0.50" "$output"

echo "--- Testing detect_changes.py ---"
run_detect "$BASE" "$HEAD"
assert_output "has_changes" "true"
assert_output "ecosystem" "rust"
assert_output_contains "dependencies" "syn"

# Clean up Cargo.lock
rm -f "$REPO_ROOT/test-projects/rust-project/Cargo.lock"

teardown_scenario
echo -e "${GREEN}Scenario 07 PASSED${NC}"
