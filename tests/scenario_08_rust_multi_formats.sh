#!/usr/bin/env bash
# Scenario 08: Rust deps in multiple formats (inline, table, dev-deps)
set -euo pipefail
source "$(dirname "$0")/helpers.sh"

setup_scenario "rust-multi-formats"

cat > "$REPO_ROOT/test-projects/rust-project/Cargo.toml" << 'EOF'
[package]
name = "test-rust-project"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0.197", features = ["derive"] }
log = "0.4.21"

[dependencies.reqwest]
version = "0.12.0"
features = ["json"]

[dev-dependencies]
tempfile = "3.10.0"
EOF

make_test_commit "add deps in various formats"

BASE=$(get_base_sha)
HEAD=$(get_head_sha)

echo "--- Testing rust_deps.py ---"
output=$(run_rust_deps "$BASE" "$HEAD")
assert_line_in "log@0.4.21" "$output"
assert_line_in "reqwest@0.12.0" "$output"
assert_line_in "tempfile@3.10.0" "$output"

echo "--- Testing detect_changes.py ---"
run_detect "$BASE" "$HEAD"
assert_output "has_changes" "true"
assert_output "ecosystem" "rust"
assert_output_contains "dependencies" "log"
assert_output_contains "dependencies" "reqwest"
assert_output_contains "dependencies" "tempfile"

teardown_scenario
echo -e "${GREEN}Scenario 08 PASSED${NC}"
