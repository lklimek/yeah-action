"""Mixed ecosystem and no-change scenarios (9-10)."""


def test_mixed_go_and_rust(scenario):
    """Scenario 09: Both Go and Rust dependencies change."""
    scenario.write_file(
        "test-projects/go-project/go.mod",
        """\
module github.com/example/test-go-project

go 1.22

require (
\tgithub.com/lib/pq v1.10.9
\tgolang.org/x/text v0.14.0
)
""",
    )
    scenario.write_file(
        "test-projects/rust-project/Cargo.toml",
        """\
[package]
name = "test-rust-project"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0.197", features = ["derive"] }
tokio = { version = "1.36.0", features = ["full"] }
""",
    )
    scenario.commit("add deps in both go and rust")

    out = scenario.run_detect()
    assert out["has_changes"] == "true"
    assert out["ecosystem"] == "mixed"
    assert "golang.org/x/text" in out["dependencies"]
    assert "tokio" in out["dependencies"]


def test_no_dep_changes(scenario):
    """Scenario 10: Non-dependency file changes only."""
    scenario.append_file(
        "test-projects/go-project/main.go",
        "// a comment change\n",
    )
    scenario.commit("change source file only")

    out = scenario.run_detect()
    assert out["has_changes"] == "false"
    assert out["ecosystem"] == "none"
