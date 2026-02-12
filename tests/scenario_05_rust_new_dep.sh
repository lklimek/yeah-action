#!/usr/bin/env bash
# Scenario 05: Add a new Rust dependency
set -euo pipefail
source "$(dirname "$0")/helpers.sh"

setup_scenario "rust-new-dep"

cat > "$REPO_ROOT/test-projects/rust-project/Cargo.toml" << 'EOF'
[package]
name = "test-rust-project"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0.197", features = ["derive"] }
tokio = { version = "1.36.0", features = ["full"] }
EOF

make_test_commit "add tokio dependency"

BASE=$(get_base_sha)
HEAD=$(get_head_sha)

echo "--- Testing rust_deps.py ---"
output=$(run_rust_deps "$BASE" "$HEAD")
assert_line_in "tokio@1.36.0" "$output"

echo "--- Testing detect_changes.py ---"
run_detect "$BASE" "$HEAD"
assert_output "has_changes" "true"
assert_output "ecosystem" "rust"
assert_output_contains "dependencies" "tokio"

teardown_scenario
echo -e "${GREEN}Scenario 05 PASSED${NC}"
