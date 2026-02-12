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
