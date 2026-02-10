#!/usr/bin/env bash
set -euo pipefail

RESULTS_DIR="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROMPT_FILE="$SCRIPT_DIR/../prompts/security-review.md"
REVIEW_INPUT="$RESULTS_DIR/review-input.txt"
AI_OUTPUT="$RESULTS_DIR/ai-review.md"
MODEL="${INPUT_MODEL:-claude-sonnet-4-20250514}"

if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "AI review skipped: no API key provided." > "$AI_OUTPUT"
  exit 0
fi

{
  cat "$PROMPT_FILE"
  echo
  echo "## Dependency changes"
  jq -r '.changes[] | "- \(.crate): \(.old // "none") -> \(.new // "none") (\(.type))"' \
    "$RESULTS_DIR/changes.json"
  echo

  if [ -f "$RESULTS_DIR/diffs.json" ]; then
    skipped=$(jq -r '.skipped' "$RESULTS_DIR/diffs.json")
    if [ "$skipped" = "true" ]; then
      reason=$(jq -r '.reason' "$RESULTS_DIR/diffs.json")
      echo "Diffs skipped: $reason"
    else
      while IFS= read -r diff; do
        crate=$(jq -r '.crate' <<< "$diff")
        old=$(jq -r '.old // "unknown"' <<< "$diff")
        new=$(jq -r '.new // "unknown"' <<< "$diff")
        path=$(jq -r '.path' <<< "$diff")
        if [ -n "$path" ] && [ -f "$RESULTS_DIR/$path" ]; then
          echo
          echo "### Diff for $crate ($old -> $new)"
          echo "```diff"
          cat "$RESULTS_DIR/$path"
          echo "```"
        fi
      done < <(jq -c '.diffs[] | select(.status == "ok")' "$RESULTS_DIR/diffs.json")
    fi
  fi
} > "$REVIEW_INPUT"

request_body=$(jq -n --arg model "$MODEL" --arg content "$(cat "$REVIEW_INPUT")" '{model:$model, max_tokens:1024, messages:[{role:"user", content:$content}] }')

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  response=$(curl -sS https://api.anthropic.com/v1/messages \
    -H "content-type: application/json" \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -d "$request_body" || true)
  ai_text=$(echo "$response" | jq -r '.content[0].text // empty' 2>/dev/null || true)
else
  response=$(curl -sS https://api.openai.com/v1/chat/completions \
    -H "content-type: application/json" \
    -H "authorization: Bearer $OPENAI_API_KEY" \
    -d "$request_body" || true)
  ai_text=$(echo "$response" | jq -r '.choices[0].message.content // empty' 2>/dev/null || true)
fi

if [ -z "$ai_text" ]; then
  echo "AI review failed to produce output." > "$AI_OUTPUT"
else
  printf '%s\n' "$ai_text" > "$AI_OUTPUT"
fi
