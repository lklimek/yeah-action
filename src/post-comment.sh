#!/usr/bin/env bash
set -euo pipefail

RESULTS_DIR="$1"
MARKER="<!-- yeah-action-review -->"
HEADER="## 🦀 YEAH — Supply Chain Review"
COMMENT_FILE="$RESULTS_DIR/comment.md"

if [ -z "${PR_NUMBER:-}" ] || [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "PR_NUMBER or GITHUB_TOKEN not set; skipping comment posting."
  exit 0
fi

{
  echo "$HEADER"
  echo "$MARKER"
  echo
  echo "### Dependency changes"
  if [ -f "$RESULTS_DIR/changes.json" ]; then
    jq -r '.changes[] | "- \(.crate): \(.old // "none") -> \(.new // "none") (\(.type))"' \
      "$RESULTS_DIR/changes.json"
  else
    echo "No dependency change data available."
  fi
  echo

  echo "### Diff generation"
  if [ -f "$RESULTS_DIR/diffs.json" ]; then
    diffs_skipped=$(jq -r '.skipped' "$RESULTS_DIR/diffs.json")
    if [ "$diffs_skipped" = "true" ]; then
      reason=$(jq -r '.reason' "$RESULTS_DIR/diffs.json")
      echo "Diffs skipped: $reason"
    else
      jq -r '.diffs[] | "- \(.crate): \(.status) \(.note // "")"' "$RESULTS_DIR/diffs.json"
    fi
  else
    echo "Diff results not available."
  fi
  echo

  echo "### Cargo audit"
  if [ -f "$RESULTS_DIR/audit.json" ]; then
    echo "<details>"
    echo "<summary>View cargo audit output</summary>"
    echo
    printf '%s\n' '```json'
    cat "$RESULTS_DIR/audit.json"
    printf '%s\n' '```'
    echo "</details>"
  else
    echo "Not run."
  fi
  echo

  echo "### Cargo deny"
  if [ -f "$RESULTS_DIR/deny.txt" ]; then
    echo "<details>"
    echo "<summary>View cargo deny output</summary>"
    echo
    printf '%s\n' '```text'
    cat "$RESULTS_DIR/deny.txt"
    printf '%s\n' '```'
    echo "</details>"
  else
    echo "Not run."
  fi
  echo

  echo "### Cargo vet"
  if [ -f "$RESULTS_DIR/vet.json" ]; then
    echo "<details>"
    echo "<summary>View cargo vet output</summary>"
    echo
    printf '%s\n' '```json'
    cat "$RESULTS_DIR/vet.json"
    printf '%s\n' '```'
    echo "</details>"
  else
    echo "Not run."
  fi
  echo

  echo "### Cargo geiger"
  if [ -f "$RESULTS_DIR/geiger.json" ]; then
    echo "<details>"
    echo "<summary>View cargo geiger output</summary>"
    echo
    printf '%s\n' '```json'
    cat "$RESULTS_DIR/geiger.json"
    printf '%s\n' '```'
    echo "</details>"
  else
    echo "Not run."
  fi
  echo

  echo "### AI security review"
  if [ -f "$RESULTS_DIR/ai-review.md" ]; then
    cat "$RESULTS_DIR/ai-review.md"
  else
    echo "Not run."
  fi
} > "$COMMENT_FILE"

comment_body=$(jq -Rs '.' < "$COMMENT_FILE")
api_url="https://api.github.com/repos/$GITHUB_REPOSITORY/issues/$PR_NUMBER/comments"
mode="${INPUT_COMMENT_MODE:-update}"

comment_id=""
if [ "$mode" = "update" ]; then
  existing=$(curl -sS -H "authorization: Bearer $GITHUB_TOKEN" -H "accept: application/vnd.github+json" "$api_url?per_page=100" || true)
  comment_id=$(echo "$existing" | jq -r --arg marker "$MARKER" '.[] | select(.body | contains($marker)) | .id' | head -n 1)
fi

if [ -n "$comment_id" ] && [ "$comment_id" != "null" ]; then
  curl -sS -X PATCH \
    -H "authorization: Bearer $GITHUB_TOKEN" \
    -H "accept: application/vnd.github+json" \
    -d "{\"body\":$comment_body}" \
    "https://api.github.com/repos/$GITHUB_REPOSITORY/issues/comments/$comment_id" >/dev/null
else
  curl -sS -X POST \
    -H "authorization: Bearer $GITHUB_TOKEN" \
    -H "accept: application/vnd.github+json" \
    -d "{\"body\":$comment_body}" \
    "$api_url" >/dev/null
fi
