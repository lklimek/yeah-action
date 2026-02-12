"""Go dependency detection scenarios (1-4)."""


def test_go_new_dep(scenario):
    """Scenario 01: Add a new Go dependency."""
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
    scenario.commit("add golang.org/x/text")

    deps = scenario.get_go_deps()
    assert any("golang.org/x/text@v0.14.0" in d for d in deps)

    out = scenario.run_detect()
    assert out["has_changes"] == "true"
    assert out["ecosystem"] == "go"
    assert "golang.org/x/text" in out["dependencies"]


def test_go_upgrade_dep(scenario):
    """Scenario 02: Upgrade an existing Go dependency."""
    scenario.write_file(
        "test-projects/go-project/go.mod",
        """\
module github.com/example/test-go-project

go 1.22

require github.com/lib/pq v1.10.10
""",
    )
    scenario.commit("upgrade lib/pq")

    deps = scenario.get_go_deps()
    assert any("github.com/lib/pq@v1.10.9..v1.10.10" in d for d in deps)

    out = scenario.run_detect()
    assert out["has_changes"] == "true"
    assert out["ecosystem"] == "go"
    assert "github.com/lib/pq" in out["dependencies"]


def test_go_multi_deps(scenario):
    """Scenario 03: Multiple Go dependency changes."""
    scenario.write_file(
        "test-projects/go-project/go.mod",
        """\
module github.com/example/test-go-project

go 1.22

require (
\tgithub.com/lib/pq v1.10.10
\tgolang.org/x/text v0.14.0
\tgolang.org/x/net v0.21.0
)
""",
    )
    scenario.commit("multi dep changes")

    deps = scenario.get_go_deps()
    dep_str = "\n".join(deps)
    assert "github.com/lib/pq@v1.10.9..v1.10.10" in dep_str
    assert "golang.org/x/text@v0.14.0" in dep_str
    assert "golang.org/x/net@v0.21.0" in dep_str

    out = scenario.run_detect()
    assert out["has_changes"] == "true"
    assert out["ecosystem"] == "go"
    assert "lib/pq" in out["dependencies"]
    assert "x/text" in out["dependencies"]
    assert "x/net" in out["dependencies"]


def test_go_gosum_transitive(scenario):
    """Scenario 04: Transitive dependency changes via go.sum only."""
    scenario.write_file(
        "test-projects/go-project/go.sum",
        """\
github.com/lib/pq v1.10.9 h1:abc123=
golang.org/x/crypto v0.18.0 h1:def456=
""",
    )
    scenario.commit("add go.sum with transitive dep")

    deps = scenario.get_go_deps()
    assert any("golang.org/x/crypto" in d for d in deps)

    out = scenario.run_detect()
    assert out["has_changes"] == "true"
    assert out["ecosystem"] == "go"
    assert "golang.org/x/crypto" in out["dependencies"]
