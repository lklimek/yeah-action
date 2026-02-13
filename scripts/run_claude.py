#!/usr/bin/env python3
"""
run_claude.py

Runs the Claude Code security review using the claude-agent-sdk Python
package. Captures the review output to a file and exposes it via
GITHUB_OUTPUT.

Requires the claude-agent-sdk Python package and Claude Code CLI to be
installed, and the ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_TURNS, and
PROMPT_FILE environment variables to be set.
"""

import asyncio
import os
import secrets
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
    """Run Claude Code review and return the output text and usage info.

    Collects messages as they stream in.  If the SDK crashes partway
    through (e.g. exit-code 1), partial output is preserved and an
    error notice is appended so it appears in the PR comment.

    Returns:
        tuple: (output_text, usage_dict) where usage_dict contains:
            - input_tokens: int
            - output_tokens: int
            - total_cost_usd: float | None
            - num_turns: int
    """
    # assistant_parts collects intermediate text blocks as a fallback in
    # case the SDK crashes before delivering a final ResultMessage.
    assistant_parts = []
    # result_text holds the authoritative output from the last ResultMessage.
    result_text = None
    error_message = None
    usage_info = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_cost_usd": None,
        "num_turns": 0,
    }

    try:
        async for message in query(
            prompt=prompt_content,
            options=ClaudeAgentOptions(
                model=claude_model,
                max_turns=int(max_turns),
                permission_mode="bypassPermissions",
                allowed_tools=[
                    "Read",
                    "Glob",
                    "Grep",
                    "Bash",
                    "WebSearch",
                    "WebFetch",
                    "Task",
                ],
            ),
        ):
            if isinstance(message, ResultMessage):
                print(
                    f"[debug] ResultMessage received "
                    f"(length={len(message.result) if message.result else 0})"
                )
                if message.result:
                    result_text = message.result

                # Accumulate usage across all ResultMessages (sub-agents
                # may each emit their own ResultMessage).
                if message.usage:
                    usage_info["input_tokens"] += message.usage.get("input_tokens", 0)
                    usage_info["output_tokens"] += message.usage.get("output_tokens", 0)
                if message.total_cost_usd is not None:
                    if usage_info["total_cost_usd"] is None:
                        usage_info["total_cost_usd"] = message.total_cost_usd
                    else:
                        usage_info["total_cost_usd"] += message.total_cost_usd
                if message.num_turns:
                    usage_info["num_turns"] += message.num_turns

                print(f"[debug] Usage so far: {usage_info}")
            elif isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(
                            f"[debug] AssistantMessage TextBlock "
                            f"(length={len(block.text)})"
                        )
                        assistant_parts.append(block.text)
    except Exception as exc:
        error_message = str(exc)
        print(f"Warning: Claude Code stream error: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        if assistant_parts:
            print(
                f"[debug] Returning {len(assistant_parts)} partial result(s) "
                f"collected before the error"
            )

    # Use the authoritative ResultMessage output when available; fall back
    # to collected AssistantMessage text blocks on SDK crash.
    if result_text is not None:
        output = result_text
    else:
        output = "\n\n".join(assistant_parts)

    if error_message:
        notice = (
            "\n\n---\n"
            "> **Warning**: The Claude Code review encountered an error and "
            "may be incomplete.\n"
            "> Please review the dependency changes manually.\n"
        )
        output = output + notice if output else notice

    return output, usage_info


def main():
    for var in ("CLAUDE_MODEL", "MAX_TURNS", "PROMPT_FILE"):
        if not os.environ.get(var):
            print(f"Error: {var} must be set", file=sys.stderr)
            sys.exit(1)

    # Strip empty auth env-vars so the CLI does not attempt an auth
    # method that was never configured (e.g. empty CLAUDE_CODE_OAUTH_TOKEN
    # would make the CLI try OAuth and hit quota errors).
    for auth_var in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"):
        if auth_var in os.environ and not os.environ[auth_var].strip():
            del os.environ[auth_var]

    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_oauth = bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"))
    if not has_api_key and not has_oauth:
        print(
            "Error: Either ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN must be set",
            file=sys.stderr,
        )
        sys.exit(1)
    if has_api_key and has_oauth:
        print(
            "Warning: Both ANTHROPIC_API_KEY and CLAUDE_CODE_OAUTH_TOKEN "
            "are set. Claude Code may show an auth conflict warning.",
            file=sys.stderr,
        )

    claude_model = os.environ["CLAUDE_MODEL"]
    max_turns_str = os.environ["MAX_TURNS"]
    prompt_file = os.environ["PROMPT_FILE"]

    try:
        max_turns = int(max_turns_str)
    except ValueError:
        print(
            f"Error: MAX_TURNS must be an integer, got '{max_turns_str}'",
            file=sys.stderr,
        )
        sys.exit(1)

    if not 1 <= max_turns <= 200:
        print(
            f"Error: MAX_TURNS must be between 1 and 200, got {max_turns}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[debug] claude_model={claude_model}")
    print(f"[debug] max_turns={max_turns}")
    print(f"[debug] prompt_file={prompt_file}")
    print(f"[debug] auth_method={'oauth' if has_oauth else 'api_key'}")

    claude_cli = shutil.which("claude")
    print(f"[debug] claude CLI path: {claude_cli}")
    if not claude_cli:
        print(
            "Error: 'claude' CLI not found on PATH. "
            "Install with: npm install -g @anthropic-ai/claude-code",
            file=sys.stderr,
        )
        sys.exit(1)

    report_dir = os.path.join(
        os.environ.get("RUNNER_TEMP", tempfile.gettempdir()),
        "yeah-action-reports",
    )
    os.makedirs(report_dir, exist_ok=True)
    review_file = os.path.join(report_dir, "dependency-review.md")

    if not os.path.isfile(prompt_file):
        print(f"Error: Prompt file not found at {prompt_file}", file=sys.stderr)
        sys.exit(1)

    with open(prompt_file) as f:
        prompt_content = f.read()

    print(f"[debug] prompt length: {len(prompt_content)} chars")
    print("Running Claude Code review...")
    sys.stdout.flush()

    usage_info = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_cost_usd": None,
        "num_turns": 0,
    }

    # Strip sensitive tokens from the environment to prevent potential
    # exfiltration through Claude's tool use.
    for var in (
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "ACTIONS_RUNTIME_TOKEN",
        "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
    ):
        os.environ.pop(var, None)

    try:
        output, usage_info = asyncio.run(
            _run_review(prompt_content, claude_model, max_turns)
        )
    except Exception as exc:
        print(f"Error: Claude Code SDK failed: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        output = (
            "> **Error**: The Claude Code review failed to run.\n"
            "> Please review the dependency changes manually.\n"
        )

    if output:
        print(output)

    if not output.strip():
        print("Warning: Claude Code produced no output.")
        output = _FALLBACK_REVIEW

    with open(review_file, "w") as f:
        f.write(output)

    print(f"Review written to {review_file}")
    print(f"Usage: {usage_info}")

    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"review_file={review_file}\n")
            f.write(f"report_dir={report_dir}\n")
            delimiter = secrets.token_hex(16)
            f.write(f"review<<{delimiter}\n")
            f.write(output[:65000])
            f.write("\n")
            f.write(f"{delimiter}\n")
            f.write(f"input_tokens={usage_info['input_tokens']}\n")
            f.write(f"output_tokens={usage_info['output_tokens']}\n")
            f.write(
                f"total_tokens={usage_info['input_tokens'] + usage_info['output_tokens']}\n"
            )
            if usage_info["total_cost_usd"] is not None:
                f.write(f"total_cost_usd={usage_info['total_cost_usd']:.6f}\n")
            else:
                f.write("total_cost_usd=\n")
            f.write(f"num_turns={usage_info['num_turns']}\n")


if __name__ == "__main__":
    main()
