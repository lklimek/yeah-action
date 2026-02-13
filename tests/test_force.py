"""Force mode scenarios (11-13)."""


def test_force_go(scenario):
    """Scenario 11: Force mode with Go module path (ecosystem inferred)."""
    out = scenario.run_detect_force("github.com/lib/pq")
    assert out["has_changes"] == "true"
    assert out["ecosystem"] == "go"
    assert out["dependencies"] == "github.com/lib/pq"


def test_force_rust(scenario):
    """Scenario 12: Force mode with Rust crate (inferred from Cargo.toml)."""
    out = scenario.run_detect_force("tokio")
    assert out["has_changes"] == "true"
    assert out["ecosystem"] == "rust"
    assert out["dependencies"] == "tokio"


def test_force_explicit_ecosystem(scenario):
    """Scenario 13: Force mode with explicit ecosystem override."""
    out = scenario.run_detect_force("my-custom-crate", ecosystem="rust")
    assert out["has_changes"] == "true"
    assert out["ecosystem"] == "rust"
    assert out["dependencies"] == "my-custom-crate"


def test_force_multiple_go(scenario):
    """Scenario 14: Force mode with multiple Go dependencies."""
    out = scenario.run_detect_force(
        "github.com/lib/pq 1.10.0..1.10.9,golang.org/x/net 0.21.0..0.23.0"
    )
    assert out["has_changes"] == "true"
    assert out["ecosystem"] == "go"
    deps = out["dependencies"].split(",")
    assert len(deps) == 2
    assert "github.com/lib/pq 1.10.0..1.10.9" in deps
    assert "golang.org/x/net 0.21.0..0.23.0" in deps


def test_force_multiple_mixed(scenario):
    """Scenario 15: Force mode with mixed Go and Rust dependencies."""
    out = scenario.run_detect_force(
        "github.com/lib/pq 1.10.0..1.10.9,serde 1.0.196..1.0.197"
    )
    assert out["has_changes"] == "true"
    assert out["ecosystem"] == "mixed"
    deps = out["dependencies"].split(",")
    assert len(deps) == 2
    assert "github.com/lib/pq 1.10.0..1.10.9" in deps
    assert "serde 1.0.196..1.0.197" in deps


def test_force_multiple_explicit_ecosystem(scenario):
    """Scenario 16: Force mode with multiple deps and explicit ecosystem."""
    out = scenario.run_detect_force(
        "tokio 1.36.0..1.37.0,serde 1.0.196..1.0.197",
        ecosystem="rust",
    )
    assert out["has_changes"] == "true"
    assert out["ecosystem"] == "rust"
    deps = out["dependencies"].split(",")
    assert len(deps) == 2
    assert "tokio 1.36.0..1.37.0" in deps
    assert "serde 1.0.196..1.0.197" in deps
