#!/usr/bin/env bash
set -euo pipefail

ensure_binstall() {
  if cargo binstall --version >/dev/null 2>&1; then
    return
  fi

  cargo install cargo-binstall --locked
}

ensure_tool() {
  local check_cmd="$1"
  local package="$2"
  if eval "$check_cmd" >/dev/null 2>&1; then
    return
  fi

  ensure_binstall
  if cargo binstall --version >/dev/null 2>&1; then
    cargo binstall -y "$package" || cargo install "$package" --locked
  else
    cargo install "$package" --locked
  fi
}
