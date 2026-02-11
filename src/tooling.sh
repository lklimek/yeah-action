#!/usr/bin/env bash
set -euo pipefail

ensure_binstall() {
  if cargo binstall --version >/dev/null 2>&1; then
    return
  fi

  if command -v curl >/dev/null 2>&1; then
    curl -L --proto '=https' --tlsv1.2 -sSf \
      https://raw.githubusercontent.com/cargo-bins/cargo-binstall/main/install-from-binstall-release.sh | bash || true
  fi

  if ! cargo binstall --version >/dev/null 2>&1; then
    cargo install cargo-binstall --locked
  fi
}

ensure_tool() {
  local check_cmd="$1"
  local package="$2"
  if eval "$check_cmd" >/dev/null 2>&1; then
    return
  fi

  ensure_binstall
  if cargo binstall -y "$package"; then
    return
  fi

  cargo install "$package" --locked
}
