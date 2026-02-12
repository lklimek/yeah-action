#!/usr/bin/env bash
set -euo pipefail

# Generates the Claude review prompt by reading a template and substituting
# the dependency argument into it. Outputs the path of the generated prompt
# file via GITHUB_OUTPUT.

ACTION_DIR="${ACTION_PATH:?ACTION_PATH must be set}"
TEMPLATE="${ACTION_DIR}/prompts/review-dependency.md"

if [[ ! -f "${TEMPLATE}" ]]; then
  echo "Error: Prompt template not found at ${TEMPLATE}" >&2
  exit 1
fi

# Determine the dependency argument: forced input > auto-detected > empty (Claude auto-detects)
if [[ -n "${INPUT_DEPENDENCY:-}" ]]; then
  ARGUMENT="${INPUT_DEPENDENCY}"
  echo "Using forced dependency input: ${ARGUMENT}"
elif [[ -n "${DEPENDENCIES:-}" ]]; then
  ARGUMENT="${DEPENDENCIES}"
  echo "Using auto-detected dependencies: ${ARGUMENT}"
else
  ARGUMENT=""
  echo "No specific dependencies provided; Claude will auto-detect from the diff"
fi

# Read the template
TEMPLATE_CONTENT=$(cat "${TEMPLATE}")

# Replace the literal string $ARGUMENTS with the dependency info.
# Use | as the sed delimiter to avoid conflicts with common path characters.
# Escape sed special characters in the replacement string.
ESCAPED_ARGUMENT=$(printf '%s\n' "${ARGUMENT}" | sed 's/[&/\]/\\&/g')
PROMPT_CONTENT=$(printf '%s\n' "${TEMPLATE_CONTENT}" | sed "s|\\\$ARGUMENTS|${ESCAPED_ARGUMENT}|g")

# Write to a temp file
PROMPT_FILE="/tmp/yeah-action-prompt-$$.md"
printf '%s\n' "${PROMPT_CONTENT}" > "${PROMPT_FILE}"

echo "Prompt written to ${PROMPT_FILE}"

# Output the file path for subsequent steps
echo "prompt_file=${PROMPT_FILE}" >> "$GITHUB_OUTPUT"
