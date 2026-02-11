#!/usr/bin/env bash
set -euo pipefail

ensure_binstall() {
  if command -v cargo-binstall >/dev/null 2>&1; then
    return
  fi

  curl_available=false
  curl_failed=false
  if command -v curl >/dev/null 2>&1; then
    curl_available=true
    temp_script="$(mktemp)"
    if curl -L --proto '=https' --tlsv1.2 -sSf \
      https://raw.githubusercontent.com/cargo-bins/cargo-binstall/main/install-from-binstall-release.sh \
      -o "$temp_script"; then
      if ! bash "$temp_script"; then
        curl_failed=true
      fi
    else
      curl_failed=true
    fi
    rm -f "$temp_script"
  fi

  if ! command -v cargo-binstall >/dev/null 2>&1; then
    if [ "$curl_available" = true ] && [ "$curl_failed" = true ]; then
      echo "cargo-binstall installer failed; using cargo install fallback." >&2
    elif [ "$curl_available" = true ]; then
      echo "cargo-binstall not found after curl install; using cargo install fallback." >&2
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
