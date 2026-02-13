# Dependency Security Review

GitHub Action that performs AI-powered security audits of dependency changes in pull requests using Claude Code.

When a PR modifies `go.mod`, `go.sum`, `Cargo.toml`, or `Cargo.lock`, the action detects the changes, runs ecosystem-specific vulnerability scanners (`govulncheck`, `cargo audit`), and invokes Claude to produce a detailed security review posted as a PR comment.

## Supported ecosystems

| Ecosystem | Manifest files | Scanner |
|---|---|---|
| Go | `go.mod`, `go.sum` | `govulncheck` |
| Rust | `Cargo.toml`, `Cargo.lock` | `cargo audit` |

Mixed-ecosystem PRs (both Go and Rust changes) are supported.

## Quick start

```yaml
# .github/workflows/dependency-review.yml
name: Dependency Security Review
on:
  pull_request:
    paths:
      - "go.mod"
      - "go.sum"
      - "Cargo.toml"
      - "Cargo.lock"

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: lklimek/yeah-action@main
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

## Authentication

Provide **one** of the following:

| Input | Description |
|---|---|
| `anthropic_api_key` | Anthropic API key |
| `oauth_token` | Claude Code OAuth token (Pro/Max/Teams/Enterprise). Generate with `claude setup-token`. |

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `anthropic_api_key` | no | | Anthropic API key |
| `oauth_token` | no | | Claude Code OAuth token |
| `dependency` | no | | Force review of specific dependencies (comma-separated, e.g. `github.com/lib/pq 1.10.0..1.11.0,serde 1.0.196..1.0.197`) |
| `ecosystem` | no | | Override ecosystem detection (`go` or `rust`) |
| `model` | no | `sonnet` | Claude model to use |
| `max_turns` | no | `50` | Maximum agentic conversation turns |

## Outputs

| Output | Description |
|---|---|
| `review` | Full markdown review text |
| `dependencies` | Dependencies that were reviewed |
| `ecosystem` | Detected ecosystem(s) |
| `input_tokens` | Input tokens used |
| `output_tokens` | Output tokens used |
| `total_tokens` | Total tokens used |

## Examples

### Review specific dependencies

```yaml
- uses: lklimek/yeah-action@main
  with:
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    dependency: "github.com/lib/pq 1.10.9..1.10.10"
```

### Use OAuth authentication

```yaml
- uses: lklimek/yeah-action@main
  with:
    oauth_token: ${{ secrets.CLAUDE_OAUTH_TOKEN }}
```

### Go project with toolchain setup

```yaml
steps:
  - uses: actions/checkout@v4
    with:
      fetch-depth: 0

  - uses: actions/setup-go@v5
    with:
      go-version-file: go.mod

  - uses: lklimek/yeah-action@main
    with:
      anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Rust project with toolchain setup

```yaml
steps:
  - uses: actions/checkout@v4
    with:
      fetch-depth: 0

  - uses: dtolnay/rust-toolchain@stable

  - uses: lklimek/yeah-action@main
    with:
      anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

## How it works

1. **Detect changes** -- diffs dependency manifests between PR base and head
2. **Install scanners** -- installs `govulncheck` and/or `cargo audit` based on ecosystem (requires the respective toolchain)
3. **Run Claude review** -- Claude Code clones upstream libraries, runs scanners, researches vulnerability databases, audits source code, and assesses codebase impact
4. **Post PR comment** -- results are posted (or updated) as a sticky comment on the PR

## License

MIT
