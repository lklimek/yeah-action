#!/usr/bin/env python3
"""
generate_prompt.py

Generates the Claude review prompt by reading a template and substituting
the dependency argument into it. Outputs the path of the generated prompt
file via GITHUB_OUTPUT.
"""

import os
import sys
import tempfile


def main():
    action_path = os.environ.get("ACTION_PATH", "")
    if not action_path:
        print("Error: ACTION_PATH must be set", file=sys.stderr)
        sys.exit(1)

    template_path = os.path.join(action_path, "prompts", "review-dependency.md")

    if not os.path.isfile(template_path):
        print(f"Error: Prompt template not found at {template_path}", file=sys.stderr)
        sys.exit(1)

    # Determine the dependency argument: forced > auto-detected > empty.
    input_dep = os.environ.get("INPUT_DEPENDENCY", "")
    dependencies = os.environ.get("DEPENDENCIES", "")

    if input_dep:
        argument = input_dep
        print(f"Using forced dependency input: {argument}")
    elif dependencies:
        argument = dependencies
        print(f"Using auto-detected dependencies: {argument}")
    else:
        argument = ""
        print(
            "No specific dependencies provided; Claude will auto-detect from the diff"
        )

    # Read the template and substitute $ARGUMENTS.
    with open(template_path) as f:
        template_content = f.read()

    prompt_content = template_content.replace("$ARGUMENTS", argument)

    # Write to a temp file.
    fd, prompt_file = tempfile.mkstemp(prefix="yeah-action-prompt-", suffix=".md")
    with os.fdopen(fd, "w") as f:
        f.write(prompt_content)

    print(f"Prompt written to {prompt_file}")

    # Output the file path for subsequent steps.
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"prompt_file={prompt_file}\n")


if __name__ == "__main__":
    main()
