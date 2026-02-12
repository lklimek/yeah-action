#!/usr/bin/env bash
# Scenario 09: Both Go and Rust dependencies change
set -euo pipefail
source "$(dirname "$0")/helpers.sh"

setup_scenario "mixed-go-and-rust"

# Modify both Go and Rust manifests
cat > "$REPO_ROOT/test-projects/go-project/go.mod" << 'EOF'
module github.com/example/test-go-project

go 1.22

require (
	github.com/lib/pq v1.10.9
	golang.org/x/text v0.14.0
)
EOF

cat > "$REPO_ROOT/test-projects/rust-project/Cargo.toml" << 'EOF'
[package]
name = "test-rust-project"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0.197", features = ["derive"] }
tokio = { version = "1.36.0", features = ["full"] }
EOF

make_test_commit "add deps in both go and rust"

BASE=$(get_base_sha)
HEAD=$(get_head_sha)

echo "--- Testing detect_changes.py ---"
run_detect "$BASE" "$HEAD"
assert_output "has_changes" "true"
assert_output "ecosystem" "mixed"
assert_output_contains "dependencies" "golang.org/x/text"
assert_output_contains "dependencies" "tokio"

teardown_scenario
echo -e "${GREEN}Scenario 09 PASSED${NC}"
