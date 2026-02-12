#!/usr/bin/env python3
"""
detect_changes.py

Main dependency change detection script for the Dependency Security Review
GitHub Action. Operates in two modes:

1. Force mode: When INPUT_DEPENDENCY is set, bypasses auto-detection and
   infers the ecosystem from the dependency name.

2. Auto-detection mode: Diffs the PR to find changed dependency manifest
   files (go.mod, go.sum, Cargo.toml, Cargo.lock) and extracts the specific
   dependencies that changed.

Outputs (written to GITHUB_OUTPUT):
    ecosystem    - "go", "rust", "mixed", or "none"
    dependencies - comma-separated list of changed dependencies
    has_changes  - "true" or "false"
"""

import os
import subprocess
import sys
from pathlib import PurePosixPath

# ---------------------------------------------------------------------------
# Ensure tomli is available before importing rust_deps (needs TOML parsing).
# Python 3.11+ has tomllib in stdlib; older versions need the tomli package.
# ---------------------------------------------------------------------------
try:
    import tomllib  # noqa: F401
except ImportError:
    try:
        import tomli  # noqa: F401
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "tomli"],
        )

# Add scripts directory to path for sibling module imports.
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from go_deps import get_go_deps  # noqa: E402
from rust_deps import get_rust_deps  # noqa: E402


def _set_output(key, value):
    """Write a key=value pair to GITHUB_OUTPUT."""
    output_file = os.environ.get("GITHUB_OUTPUT", "")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"{key}={value}\n")


def _run_git(*args):
    """Run a git command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout if result.returncode == 0 else ""
    except OSError:
        return ""


def _has_cargo_toml():
    """Check if a Cargo.toml exists within 3 levels of the current directory."""
    for root, _dirs, files in os.walk("."):
        if root.count(os.sep) > 3:
            continue
        if "Cargo.toml" in files:
            return True
    return False


def _force_mode():
    """Handle force mode when INPUT_DEPENDENCY is set."""
    dep = os.environ["INPUT_DEPENDENCY"]
    print(f"Force mode: dependency explicitly provided as '{dep}'")

    ecosystem = os.environ.get("INPUT_ECOSYSTEM", "")

    if not ecosystem:
        # Infer ecosystem: Go modules start with a domain (contain a dot
        # before the first slash), e.g. github.com/lib/pq.
        first_slash = dep.find("/")
        if first_slash > 0 and "." in dep[:first_slash]:
            ecosystem = "go"
        elif _has_cargo_toml():
            ecosystem = "rust"
        else:
            ecosystem = "go"

    print(f"Inferred ecosystem: {ecosystem}")

    _set_output("has_changes", "true")
    _set_output("ecosystem", ecosystem)
    _set_output("dependencies", dep)


def _auto_detect_mode():
    """Handle auto-detection mode: scan PR diff for dependency changes."""
    print("Auto-detection mode: scanning PR diff for dependency changes")

    action_path = os.environ.get("ACTION_PATH", "")
    if not action_path:
        print("Error: ACTION_PATH environment variable is required",
              file=sys.stderr)
        sys.exit(1)

    # Determine BASE_SHA and HEAD_SHA with fallbacks.
    base_sha = os.environ.get("BASE_SHA", "")
    head_sha = os.environ.get("HEAD_SHA", "")

    if not base_sha:
        ref = _run_git(
            "symbolic-ref", "refs/remotes/origin/HEAD"
        ).strip()
        default_branch = ref.replace("refs/remotes/origin/", "") if ref else "main"
        base_sha = _run_git(
            "merge-base", f"origin/{default_branch}", "HEAD"
        ).strip()
        if not base_sha:
            base_sha = _run_git("rev-parse", "HEAD~1").strip()
        if not base_sha:
            print("Error: Could not determine BASE_SHA.", file=sys.stderr)
            sys.exit(1)
        print(f"BASE_SHA not provided; using fallback: {base_sha}")

    if not head_sha:
        head_sha = _run_git("rev-parse", "HEAD").strip()
        if not head_sha:
            print("Error: Could not determine HEAD_SHA.", file=sys.stderr)
            sys.exit(1)
        print(f"HEAD_SHA not provided; using fallback: {head_sha}")

    # Get changed files.
    changed_files = _run_git(
        "diff", "--name-only", f"{base_sha}...{head_sha}"
    ).strip()

    if not changed_files:
        print(f"No changed files detected between {base_sha} and {head_sha}")
        _set_output("has_changes", "false")
        _set_output("ecosystem", "none")
        _set_output("dependencies", "")
        return

    print("Changed files:")
    print(changed_files)

    # Detect Go and Rust dependency file changes by checking basenames.
    file_list = [f for f in changed_files.splitlines() if f.strip()]
    has_go = any(
        PurePosixPath(f).name in ("go.mod", "go.sum") for f in file_list
    )
    has_rust = any(
        PurePosixPath(f).name in ("Cargo.toml", "Cargo.lock")
        for f in file_list
    )

    if has_go:
        print("Detected Go dependency file changes")
    if has_rust:
        print("Detected Rust dependency file changes")

    if not has_go and not has_rust:
        print("No dependency manifest files changed in this PR")
        _set_output("has_changes", "false")
        _set_output("ecosystem", "none")
        _set_output("dependencies", "")
        return

    # Extract changed dependencies.
    go_deps = []
    rust_deps = []

    if has_go:
        print("Extracting Go dependency changes...")
        try:
            go_deps = get_go_deps(base_sha, head_sha)
        except Exception as exc:
            print(f"Warning: Go dependency extraction failed: {exc}")
        if go_deps:
            print("Go dependencies changed:")
            print("\n".join(go_deps))
        else:
            print("Go manifest files changed but no individual dependency "
                  "changes detected")

    if has_rust:
        print("Extracting Rust dependency changes...")
        try:
            rust_deps = get_rust_deps(base_sha, head_sha)
        except Exception as exc:
            print(f"Warning: Rust dependency extraction failed: {exc}")
        if rust_deps:
            print("Rust dependencies changed:")
            print("\n".join(rust_deps))
        else:
            print("Rust manifest files changed but no individual dependency "
                  "changes detected")

    # Determine ecosystem label.
    if has_go and has_rust:
        ecosystem = "mixed"
    elif has_go:
        ecosystem = "go"
    else:
        ecosystem = "rust"

    # Combine into comma-separated list.
    all_deps = go_deps + rust_deps
    dependencies = ",".join(all_deps)

    # Manifest files changed → flag for review even without specific deps.
    has_changes = "true"

    print(f"\nSummary:")
    print(f"  ecosystem:    {ecosystem}")
    print(f"  dependencies: {dependencies}")
    print(f"  has_changes:  {has_changes}")

    _set_output("has_changes", has_changes)
    _set_output("ecosystem", ecosystem)
    _set_output("dependencies", dependencies)


def main():
    if os.environ.get("INPUT_DEPENDENCY", ""):
        _force_mode()
    else:
        _auto_detect_mode()


if __name__ == "__main__":
    main()
