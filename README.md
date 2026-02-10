# YEAH — Rust Supply Chain AI Review

**Your CI says YEAH only to safe dependencies.**

YEAH is a reusable GitHub Action that reviews Rust dependency updates in pull requests. It detects Cargo.lock changes, generates diffs for updated crates, runs supply-chain security tools, and posts a single sticky review comment in the PR.

## Features

- Detects added/removed/updated crates by comparing `Cargo.lock` to the base branch
- Generates crate diffs via `cargo vet diff` (when configured)
- Runs `cargo audit`, `cargo deny`, and `cargo geiger` on demand
- Sends diffs to an LLM for a security-focused review
- Posts a sticky PR comment that updates instead of spamming
- Graceful degradation when API keys or `cargo vet` config are missing

## Usage

```yaml
# .github/workflows/yeah.yml
name: YEAH — Supply Chain Review
on:
  pull_request:
    paths: ['Cargo.toml', 'Cargo.lock', '**/Cargo.toml']

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

      - uses: dtolnay/rust-toolchain@stable

      - uses: lklimek/yeah-action@v1
        with:
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

> **Note:** `fetch-depth: 0` is required so YEAH can compare `Cargo.lock` with the base branch.

## Inputs

| Name | Description | Default |
| --- | --- | --- |
| `anthropic-api-key` | Anthropic API key for Claude | _none_ |
| `openai-api-key` | OpenAI API key (alternative to Claude) | _none_ |
| `model` | Model to use | `claude-sonnet-4-20250514` |
| `cargo-deny` | Run cargo deny check | `true` |
| `cargo-audit` | Run cargo audit | `true` |
| `cargo-vet` | Run cargo vet (check audit status + generate diffs) | `true` |
| `cargo-geiger` | Run cargo geiger on changed crates | `true` |
| `project-path` | Path to the Rust project (relative to repository root) | `.` |
| `max-diff-size` | Max diff size per crate in bytes before truncation | `50000` |
| `comment-mode` | `create` (new comment) or `update` (sticky comment) | `update` |

## Outputs

The action posts a comment that begins with:

```
## 🦀 YEAH — Supply Chain Review
```

The comment contains:
- Dependency change summary
- Diff generation status
- Outputs from `cargo audit`, `cargo deny`, `cargo vet`, and `cargo geiger`
- AI review summary (if configured)

## Graceful Degradation

- If no API key is provided, YEAH skips the AI review and posts only tool results.
- If `cargo vet` is not initialized (missing `supply-chain` config), diffs are skipped.

## Tool Configuration Requirements

- **cargo audit:** Requires a `Cargo.lock` file for the target project.
- **cargo deny:** Provide a `deny.toml` policy file in the project directory (or disable the tool).
- **cargo vet:** Run `cargo vet init` to generate `supply-chain/config.toml` and `supply-chain/audits.toml`.
- **cargo geiger:** No additional configuration required.

## License

MIT
