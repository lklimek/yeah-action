#!/usr/bin/env bash
set -euo pipefail

# Installs Claude Code CLI and runs the security review prompt.
# Captures the review output to a file and exposes it via GITHUB_OUTPUT.

: "${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY must be set}"
: "${CLAUDE_MODEL:?CLAUDE_MODEL must be set}"
: "${MAX_TURNS:?MAX_TURNS must be set}"
: "${PROMPT_FILE:?PROMPT_FILE must be set}"

REVIEW_FILE="/tmp/yeah-action-review-$$.md"

# ---------------------------------------------------------------
# Install Claude Code CLI
# ---------------------------------------------------------------
echo "Installing Claude Code CLI..."
npm install -g @anthropic-ai/claude-code

# ---------------------------------------------------------------
# Read the prompt
# ---------------------------------------------------------------
if [[ ! -f "${PROMPT_FILE}" ]]; then
  echo "Error: Prompt file not found at ${PROMPT_FILE}" >&2
  exit 1
fi

PROMPT_CONTENT=$(cat "${PROMPT_FILE}")

# ---------------------------------------------------------------
# Run Claude Code
# ---------------------------------------------------------------
echo "Running Claude Code review..."

# Use --dangerously-skip-permissions in CI to avoid hanging on tool
# approval prompts. The CI runner is already sandboxed and ephemeral.
# pipefail is already set; capture exit codes from the pipe.
# Pipe: printf (0) | claude (1) | tee (2)
set +e
printf '%s' "${PROMPT_CONTENT}" | claude \
  -p \
  --model "${CLAUDE_MODEL}" \
  --max-turns "${MAX_TURNS}" \
  --output-format text \
  --verbose \
  --dangerously-skip-permissions \
  | tee "${REVIEW_FILE}"
PIPE_STATUSES=("${PIPESTATUS[@]}")
set -e

CLAUDE_EXIT="${PIPE_STATUSES[1]}"
echo ""
echo "Claude Code exited with status ${CLAUDE_EXIT}"

# ---------------------------------------------------------------
# Handle failure or empty output
# ---------------------------------------------------------------
if [[ ${CLAUDE_EXIT} -ne 0 ]] || [[ ! -s "${REVIEW_FILE}" ]]; then
  echo "Warning: Claude Code exited with status ${CLAUDE_EXIT} or produced no output."
  cat > "${REVIEW_FILE}" <<'FALLBACK'
> **Note**: The automated Claude Code review could not be completed.
> This may be due to a timeout, API error, or insufficient context.
> Please review the dependency changes manually.
FALLBACK
fi

echo "Review written to ${REVIEW_FILE}"

# ---------------------------------------------------------------
# Output the review file path and content
# ---------------------------------------------------------------
echo "review_file=${REVIEW_FILE}" >> "$GITHUB_OUTPUT"

{
  echo "review<<YEAH_ACTION_EOF"
  head -c 65000 "${REVIEW_FILE}"
  echo ""
  echo "YEAH_ACTION_EOF"
} >> "$GITHUB_OUTPUT"
