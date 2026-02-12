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
# Build the list of allowed tools
# ---------------------------------------------------------------
ALLOWED_TOOLS=(
  --allowedTools Read
  --allowedTools Glob
  --allowedTools Grep
  --allowedTools WebSearch
  --allowedTools WebFetch
  --allowedTools Task
  --allowedTools "Bash(git diff:*)"
  --allowedTools "Bash(git log:*)"
  --allowedTools "Bash(git show:*)"
  --allowedTools "Bash(git clone:*)"
  --allowedTools "Bash(git checkout:*)"
  --allowedTools "Bash(rm -rf /tmp/claude/*)"
  --allowedTools "Bash(gh api:*)"
  --allowedTools "Bash(curl:*)"
  --allowedTools "Bash(ls:*)"
  --allowedTools "Bash(find:*)"
  --allowedTools "Bash(mkdir:*)"
)

# Ecosystem-specific tools
ECOSYSTEM="${ECOSYSTEM:-}"

if [[ "${ECOSYSTEM}" == *"go"* ]]; then
  ALLOWED_TOOLS+=(
    --allowedTools "Bash(go list:*)"
    --allowedTools "Bash(govulncheck:*)"
    --allowedTools "Bash(go mod:*)"
  )
fi

if [[ "${ECOSYSTEM}" == *"rust"* ]]; then
  ALLOWED_TOOLS+=(
    --allowedTools "Bash(cargo audit:*)"
    --allowedTools "Bash(cargo tree:*)"
  )
fi

# ---------------------------------------------------------------
# Run Claude Code
# ---------------------------------------------------------------
echo "Running Claude Code review..."

set +e
printf '%s' "${PROMPT_CONTENT}" | claude \
  -p \
  --model "${CLAUDE_MODEL}" \
  --max-turns "${MAX_TURNS}" \
  --output-format text \
  "${ALLOWED_TOOLS[@]}" \
  > "${REVIEW_FILE}"
CLAUDE_EXIT=$?
set -e

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
