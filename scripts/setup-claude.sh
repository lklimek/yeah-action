#!/usr/bin/env bash
set -euo pipefail

# Sets up the Claude Code environment in the workspace by copying
# the action's CLAUDE.md and agent definitions into the workspace's
# .claude/ directory.

WORKSPACE="${GITHUB_WORKSPACE:-.}"
ACTION_DIR="${ACTION_PATH:?ACTION_PATH must be set}"

CLAUDE_DIR="${WORKSPACE}/.claude"
AGENTS_DIR="${CLAUDE_DIR}/agents"

# Ensure .claude/agents/ directory exists
mkdir -p "${AGENTS_DIR}"

# Handle CLAUDE.md: append if it already exists, otherwise copy
ACTION_CLAUDE_MD="${ACTION_DIR}/.claude-action/CLAUDE.md"

if [[ -f "${ACTION_CLAUDE_MD}" ]]; then
  if [[ -f "${CLAUDE_DIR}/CLAUDE.md" ]]; then
    echo "Existing CLAUDE.md found in workspace; appending action instructions."
    {
      echo ""
      echo "---"
      echo ""
      cat "${ACTION_CLAUDE_MD}"
    } >> "${CLAUDE_DIR}/CLAUDE.md"
  else
    echo "No existing CLAUDE.md found; copying action CLAUDE.md."
    cp "${ACTION_CLAUDE_MD}" "${CLAUDE_DIR}/CLAUDE.md"
  fi
else
  echo "Warning: No CLAUDE.md found at ${ACTION_CLAUDE_MD}; skipping."
fi

# Copy all agents from the action into the workspace
ACTION_AGENTS_DIR="${ACTION_DIR}/.claude-action/agents"

if [[ -d "${ACTION_AGENTS_DIR}" ]] && ls "${ACTION_AGENTS_DIR}"/* >/dev/null 2>&1; then
  echo "Copying agents from action to workspace."
  cp -r "${ACTION_AGENTS_DIR}"/* "${AGENTS_DIR}/"
else
  echo "No agents found in action; skipping agent copy."
fi

echo "Claude environment setup complete in ${CLAUDE_DIR}"
