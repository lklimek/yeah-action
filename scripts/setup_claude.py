#!/usr/bin/env python3
"""
setup_claude.py

Sets up the Claude Code environment in the workspace by copying the action's
CLAUDE.md and agent definitions into the workspace's .claude/ directory.
"""

import os
import shutil
import sys
from pathlib import Path


def main():
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", "."))
    action_dir = os.environ.get("ACTION_PATH", "")
    if not action_dir:
        print("Error: ACTION_PATH must be set", file=sys.stderr)
        sys.exit(1)
    action_dir = Path(action_dir)

    claude_dir = workspace / ".claude"
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    # Handle CLAUDE.md: append if it already exists, otherwise copy.
    action_claude_md = action_dir / ".claude-action" / "CLAUDE.md"

    if action_claude_md.is_file():
        target_claude_md = claude_dir / "CLAUDE.md"
        if target_claude_md.is_file():
            print(
                "Existing CLAUDE.md found in workspace; appending action instructions."
            )
            with open(target_claude_md, "a") as f:
                f.write("\n---\n\n")
                f.write(action_claude_md.read_text())
        else:
            print("No existing CLAUDE.md found; copying action CLAUDE.md.")
            shutil.copy2(action_claude_md, target_claude_md)
    else:
        print(f"Warning: No CLAUDE.md found at {action_claude_md}; skipping.")

    # Copy all agents from the action into the workspace.
    action_agents_dir = action_dir / ".claude-action" / "agents"

    if action_agents_dir.is_dir() and any(action_agents_dir.iterdir()):
        print("Copying agents from action to workspace.")
        for agent_file in action_agents_dir.iterdir():
            if agent_file.is_file():
                shutil.copy2(agent_file, agents_dir / agent_file.name)
    else:
        print("No agents found in action; skipping agent copy.")

    print(f"Claude environment setup complete in {claude_dir}")


if __name__ == "__main__":
    main()
