#!/usr/bin/env python3
"""
run_claude.py

Installs Claude Code CLI and runs the security review prompt.
Captures the review output to a file and exposes it via GITHUB_OUTPUT.
"""

import os
import subprocess
import sys
import tempfile


_FALLBACK_REVIEW = (
    "> **Note**: The automated Claude Code review could not be completed.\n"
    "> This may be due to a timeout, API error, or insufficient context.\n"
    "> Please review the dependency changes manually.\n"
)


def main():
    # Validate required environment variables.
    for var in ("ANTHROPIC_API_KEY", "CLAUDE_MODEL", "MAX_TURNS", "PROMPT_FILE"):
        if not os.environ.get(var):
            print(f"Error: {var} must be set", file=sys.stderr)
            sys.exit(1)

    claude_model = os.environ["CLAUDE_MODEL"]
    max_turns = os.environ["MAX_TURNS"]
    prompt_file = os.environ["PROMPT_FILE"]

    fd, review_file = tempfile.mkstemp(
        prefix="yeah-action-review-", suffix=".md", dir="/tmp"
    )
    os.close(fd)

    # Install Claude Code CLI.
    print("Installing Claude Code CLI...")
    subprocess.run(
        ["npm", "install", "-g", "@anthropic-ai/claude-code"],
        check=True,
    )

    # Read the prompt.
    if not os.path.isfile(prompt_file):
        print(f"Error: Prompt file not found at {prompt_file}",
              file=sys.stderr)
        sys.exit(1)

    with open(prompt_file) as f:
        prompt_content = f.read()

    # Run Claude Code.
    print("Running Claude Code review...")
    proc = subprocess.run(
        [
            "claude",
            "-p",
            "--model", claude_model,
            "--max-turns", max_turns,
            "--output-format", "text",
            "--verbose",
            "--dangerously-skip-permissions",
        ],
        input=prompt_content,
        capture_output=True,
        text=True,
        check=False,
    )

    claude_exit = proc.returncode
    output = proc.stdout or ""

    # Print output for CI logs (like tee).
    if output:
        print(output)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)

    print(f"\nClaude Code exited with status {claude_exit}")

    # Handle failure or empty output.
    if claude_exit != 0 or not output.strip():
        print(f"Warning: Claude Code exited with status {claude_exit} or "
              "produced no output.")
        output = _FALLBACK_REVIEW

    with open(review_file, "w") as f:
        f.write(output)

    print(f"Review written to {review_file}")

    # Write outputs.
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"review_file={review_file}\n")
            f.write("review<<YEAH_ACTION_EOF\n")
            # Truncate to 65000 chars to stay within GitHub limits.
            f.write(output[:65000])
            f.write("\n")
            f.write("YEAH_ACTION_EOF\n")


if __name__ == "__main__":
    main()
