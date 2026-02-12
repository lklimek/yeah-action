#!/usr/bin/env bash
# Scenario 06: Upgrade an existing Rust dependency
set -euo pipefail
source "$(dirname "$0")/helpers.sh"

setup_scenario "rust-upgrade-dep"

cat > "$REPO_ROOT/test-projects/rust-project/Cargo.toml" << 'EOF'
[package]
name = "test-rust-project"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0.210", features = ["derive"] }
EOF

make_test_commit "upgrade serde"

BASE=$(get_base_sha)
HEAD=$(get_head_sha)

echo "--- Testing rust_deps.py ---"
output=$(run_rust_deps "$BASE" "$HEAD")
assert_line_in "serde@1.0.197..1.0.210" "$output"

echo "--- Testing detect_changes.py ---"
run_detect "$BASE" "$HEAD"
assert_output "has_changes" "true"
assert_output "ecosystem" "rust"
assert_output_contains "dependencies" "serde"

teardown_scenario
echo -e "${GREEN}Scenario 06 PASSED${NC}"
