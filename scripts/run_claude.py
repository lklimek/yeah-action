#!/usr/bin/env python3
"""
run_claude.py

Runs the Claude Code security review using the claude-code-sdk Python
package. Captures the review output to a file and exposes it via
GITHUB_OUTPUT.

Requires the @anthropic-ai/claude-code npm package to be installed
(handled by the action.yml workflow).
"""

import asyncio
import os
import pathlib
import sys
import tempfile

from claude_code_sdk import ClaudeCodeOptions, query
from claude_code_sdk.types import AssistantMessage, ResultMessage, TextBlock


_FALLBACK_REVIEW = (
    "> **Note**: The automated Claude Code review could not be completed.\n"
    "> This may be due to a timeout, API error, or insufficient context.\n"
    "> Please review the dependency changes manually.\n"
)


async def _run_review(prompt_content, claude_model, max_turns):
    """Run Claude Code review and return the output text."""
    result_parts = []

    async for message in query(
        prompt=prompt_content,
        options=ClaudeCodeOptions(
            model=claude_model,
            max_turns=int(max_turns),
            permission_mode="bypassPermissions",
            cwd=str(pathlib.Path.cwd()),
        ),
    ):
        if isinstance(message, ResultMessage):
            if message.result:
                result_parts.append(message.result)
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    result_parts.append(block.text)

    return "\n\n".join(result_parts)


def main():
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

    if not os.path.isfile(prompt_file):
        print(f"Error: Prompt file not found at {prompt_file}",
              file=sys.stderr)
        sys.exit(1)

    with open(prompt_file) as f:
        prompt_content = f.read()

    print("Running Claude Code review...")
    try:
        output = asyncio.run(
            _run_review(prompt_content, claude_model, max_turns)
        )
    except Exception as exc:
        print(f"Warning: Claude Code SDK error: {exc}", file=sys.stderr)
        output = ""

    if output:
        print(output)

    if not output.strip():
        print("Warning: Claude Code produced no output.")
        output = _FALLBACK_REVIEW

    with open(review_file, "w") as f:
        f.write(output)

    print(f"Review written to {review_file}")

    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"review_file={review_file}\n")
            f.write("review<<YEAH_ACTION_EOF\n")
            f.write(output[:65000])
            f.write("\n")
            f.write("YEAH_ACTION_EOF\n")


if __name__ == "__main__":
    main()
