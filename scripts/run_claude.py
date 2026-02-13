#!/usr/bin/env python3
"""
run_claude.py

Runs the Claude Code security review using the claude-agent-sdk Python
package. Captures the review output to a file and exposes it via
GITHUB_OUTPUT.

Requires the @anthropic-ai/claude-code npm package to be installed
(handled by the action.yml workflow).
"""

import asyncio
import os
import shutil
import sys
import tempfile
import traceback

from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock


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
        options=ClaudeAgentOptions(
            model=claude_model,
            max_turns=int(max_turns),
            permission_mode="bypassPermissions",
        ),
    ):
        if isinstance(message, ResultMessage):
            print(f"[debug] ResultMessage received "
                  f"(length={len(message.result) if message.result else 0})")
            if message.result:
                result_parts.append(message.result)
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"[debug] AssistantMessage TextBlock "
                          f"(length={len(block.text)})")
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

    print(f"[debug] claude_model={claude_model}")
    print(f"[debug] max_turns={max_turns}")
    print(f"[debug] prompt_file={prompt_file}")

    claude_cli = shutil.which("claude")
    print(f"[debug] claude CLI path: {claude_cli}")
    if not claude_cli:
        print("Error: 'claude' CLI not found on PATH. "
              "Install with: npm install -g @anthropic-ai/claude-code",
              file=sys.stderr)
        sys.exit(1)

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

    print(f"[debug] prompt length: {len(prompt_content)} chars")
    print("Running Claude Code review...")
    sys.stdout.flush()
    try:
        output = asyncio.run(
            _run_review(prompt_content, claude_model, max_turns)
        )
    except Exception as exc:
        print(f"Error: Claude Code SDK failed: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
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
