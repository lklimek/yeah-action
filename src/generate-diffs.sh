#!/usr/bin/env bash
set -euo pipefail

RESULTS_DIR="$1"
CHANGES_FILE="$RESULTS_DIR/changes.json"
DIFF_DIR="$RESULTS_DIR/diffs"
MAX_DIFF_SIZE="${INPUT_MAX_DIFF_SIZE:-50000}"

mkdir -p "$DIFF_DIR"

if [ "${INPUT_CARGO_VET:-true}" != "true" ]; then
  jq -n '{skipped:true, reason:"cargo vet disabled", diffs:[]}' > "$RESULTS_DIR/diffs.json"
  exit 0
fi

if [ ! -f "supply-chain/config.toml" ] && [ ! -f "supply-chain/audits.toml" ]; then
  jq -n '{skipped:true, reason:"cargo vet not initialized", diffs:[]}' > "$RESULTS_DIR/diffs.json"
  exit 0
fi

ensure_binstall() {
  if cargo binstall --version >/dev/null 2>&1; then
    return
  fi

  if command -v curl >/dev/null 2>&1; then
    curl -sSfL https://raw.githubusercontent.com/cargo-bins/cargo-binstall/main/install-from-binstall-release.sh | bash || true
  fi

  if ! cargo binstall --version >/dev/null 2>&1; then
    cargo install cargo-binstall --locked
  fi
}

if ! cargo vet --version >/dev/null 2>&1; then
  ensure_binstall
  if cargo binstall --version >/dev/null 2>&1; then
    cargo binstall -y cargo-vet || cargo install cargo-vet --locked
  else
    cargo install cargo-vet --locked
  fi
fi

diffs='[]'

while IFS= read -r change; do
  crate=$(jq -r '.crate' <<< "$change")
  old=$(jq -c '.old' <<< "$change")
  new=$(jq -c '.new' <<< "$change")
  change_type=$(jq -r '.type' <<< "$change")

  status="skipped"
  note=""
  diff_path=""
  truncated=false

  if [ "$change_type" = "updated" ]; then
    if [[ "$old" == *","* || "$new" == *","* ]]; then
      note="multiple versions changed"
    else
      safe_name=$(printf '%s' "$crate" | tr '/ ' '__')
      old_value=$(jq -r '.old' <<< "$change")
      new_value=$(jq -r '.new' <<< "$change")
      diff_file="$DIFF_DIR/${safe_name}-${old_value}-to-${new_value}.diff"
      if cargo vet diff "$crate" "$old_value" "$new_value" > "$diff_file" 2>&1; then
        status="ok"
      else
        status="error"
        note="cargo vet diff failed"
      fi

      if [ -f "$diff_file" ]; then
        diff_size=$(wc -c < "$diff_file" | tr -d ' ')
        if [ "$diff_size" -gt "$MAX_DIFF_SIZE" ]; then
          head -c "$MAX_DIFF_SIZE" "$diff_file" > "$diff_file.tmp"
          mv "$diff_file.tmp" "$diff_file"
          truncated=true
        fi
        diff_path="diffs/$(basename "$diff_file")"
      fi
    fi
  else
    note="crate was $change_type"
  fi

  diffs=$(jq -n \
    --argjson diffs "$diffs" \
    --arg crate "$crate" \
    --argjson old "$old" \
    --argjson new "$new" \
    --arg status "$status" \
    --arg note "$note" \
    --arg path "$diff_path" \
    --argjson truncated "$truncated" \
    '$diffs + [{crate:$crate, old:$old, new:$new, status:$status, note:$note, path:$path, truncated:$truncated}]')

done < <(jq -c '.changes[]' "$CHANGES_FILE")

jq -n --argjson diffs "$diffs" '{skipped:false, reason:null, diffs:$diffs}' > "$RESULTS_DIR/diffs.json"
