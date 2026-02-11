#!/usr/bin/env bash
set -euo pipefail

ensure_binstall() {
  if command -v cargo-binstall >/dev/null 2>&1; then
    return
  fi

  curl_available=false
  curl_success=false
  if command -v curl >/dev/null 2>&1; then
    curl_available=true
    if temp_script="$(mktemp)"; then
      if curl -L --proto '=https' --tlsv1.2 -sSf \
        https://raw.githubusercontent.com/cargo-bins/cargo-binstall/main/install-from-binstall-release.sh \
        -o "$temp_script"; then
        if bash "$temp_script"; then
          curl_success=true
        fi
      fi
      rm -f "$temp_script"
    fi
  fi

  if ! command -v cargo-binstall >/dev/null 2>&1; then
    if [ "$curl_available" = true ] && [ "$curl_success" = true ]; then
      echo "cargo-binstall not found after installer (PATH or install issue); using cargo install fallback." >&2
    elif [ "$curl_available" = true ]; then
      echo "cargo-binstall installer failed; using cargo install fallback." >&2
    else
      echo "curl not available; using cargo install fallback." >&2
    fi
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
