"""Rust dependency detection scenarios (5-8)."""


def test_rust_new_dep(scenario):
    """Scenario 05: Add a new Rust dependency."""
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
    scenario.commit("add tokio dependency")

    deps = scenario.get_rust_deps()
    assert any("tokio@1.36.0" in d for d in deps)

    out = scenario.run_detect()
    assert out["has_changes"] == "true"
    assert out["ecosystem"] == "rust"
    assert "tokio" in out["dependencies"]


def test_rust_upgrade_dep(scenario):
    """Scenario 06: Upgrade an existing Rust dependency."""
    scenario.write_file(
        "test-projects/rust-project/Cargo.toml",
        """\
[package]
name = "test-rust-project"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0.210", features = ["derive"] }
""",
    )
    scenario.commit("upgrade serde")

    deps = scenario.get_rust_deps()
    assert any("serde@1.0.197..1.0.210" in d for d in deps)

    out = scenario.run_detect()
    assert out["has_changes"] == "true"
    assert out["ecosystem"] == "rust"
    assert "serde" in out["dependencies"]


def test_rust_lock_transitive(scenario):
    """Scenario 07: Transitive dependency changes via Cargo.lock."""
    scenario.write_file(
        "test-projects/rust-project/Cargo.lock",
        """\
[[package]]
name = "test-rust-project"
version = "0.1.0"

[[package]]
name = "serde"
version = "1.0.197"

[[package]]
name = "syn"
version = "2.0.50"
""",
    )
    scenario.commit("add Cargo.lock with transitive deps")

    deps = scenario.get_rust_deps()
    assert any("syn@2.0.50" in d for d in deps)

    out = scenario.run_detect()
    assert out["has_changes"] == "true"
    assert out["ecosystem"] == "rust"
    assert "syn" in out["dependencies"]


def test_rust_multi_formats(scenario):
    """Scenario 08: Rust deps in multiple formats (inline, table, dev-deps)."""
    scenario.write_file(
        "test-projects/rust-project/Cargo.toml",
        """\
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
""",
    )
    scenario.commit("add deps in various formats")

    deps = scenario.get_rust_deps()
    dep_str = "\n".join(deps)
    assert "log@0.4.21" in dep_str
    assert "reqwest@0.12.0" in dep_str
    assert "tempfile@3.10.0" in dep_str

    out = scenario.run_detect()
    assert out["has_changes"] == "true"
    assert out["ecosystem"] == "rust"
    assert "log" in out["dependencies"]
    assert "reqwest" in out["dependencies"]
    assert "tempfile" in out["dependencies"]
