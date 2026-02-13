#!/usr/bin/env python3
"""
detect_changes.py

Main dependency change detection script for the Dependency Security Review
GitHub Action. Uses GitPython for all repository operations. Operates in
two modes:

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
import sys
from pathlib import PurePosixPath

import git

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


def _has_cargo_toml():
    """Check if a Cargo.toml exists within 3 levels of the current directory."""
    for root, _dirs, files in os.walk("."):
        if root.count(os.sep) > 3:
            continue
        if "Cargo.toml" in files:
            return True
    return False


def _infer_ecosystem(dep_name):
    """Infer ecosystem for a single dependency name.

    Returns "go" if the name looks like a Go module path (e.g.
    ``github.com/lib/pq``), "rust" if a Cargo.toml is found nearby,
    or "go" as fallback.
    """
    # Strip version range if present (e.g. "github.com/lib/pq 1.10.0..1.10.9")
    name = dep_name.strip().split()[0]
    first_slash = name.find("/")
    if first_slash > 0 and "." in name[:first_slash]:
        return "go"
    if _has_cargo_toml():
        return "rust"
    return "go"


def _force_mode():
    """Handle force mode when INPUT_DEPENDENCY is set.

    Supports a single dependency or multiple comma-separated dependencies.
    When multiple dependencies span both Go and Rust the ecosystem is
    reported as "mixed".
    """
    raw = os.environ["INPUT_DEPENDENCY"]
    deps = [d.strip() for d in raw.split(",") if d.strip()]
    print(f"Force mode: {len(deps)} dependency(ies) provided")

    explicit_ecosystem = os.environ.get("INPUT_ECOSYSTEM", "")

    if explicit_ecosystem:
        ecosystem = explicit_ecosystem
    else:
        ecosystems = {_infer_ecosystem(d) for d in deps}
        if ecosystems == {"go"}:
            ecosystem = "go"
        elif ecosystems == {"rust"}:
            ecosystem = "rust"
        else:
            ecosystem = "mixed"

    print(f"Dependencies: {', '.join(deps)}")
    print(f"Ecosystem: {ecosystem}")

    _set_output("has_changes", "true")
    _set_output("ecosystem", ecosystem)
    _set_output("dependencies", ",".join(deps))


def _auto_detect_mode():
    """Handle auto-detection mode: scan PR diff for dependency changes."""
    print("Auto-detection mode: scanning PR diff for dependency changes")

    action_path = os.environ.get("ACTION_PATH", "")
    if not action_path:
        print("Error: ACTION_PATH environment variable is required",
              file=sys.stderr)
        sys.exit(1)

    repo = git.Repo(".", search_parent_directories=True)

    base_sha = os.environ.get("BASE_SHA", "")
    head_sha = os.environ.get("HEAD_SHA", "")

    if not base_sha:
        try:
            ref = repo.git.symbolic_ref("refs/remotes/origin/HEAD")
            default_branch = ref.replace("refs/remotes/origin/", "")
        except git.GitCommandError:
            default_branch = "main"

        try:
            base_sha = repo.git.merge_base(
                f"origin/{default_branch}", "HEAD",
            ).strip()
        except git.GitCommandError:
            pass

        if not base_sha:
            try:
                base_sha = repo.git.rev_parse("HEAD~1").strip()
            except git.GitCommandError:
                pass

        if not base_sha:
            print("Error: Could not determine BASE_SHA.", file=sys.stderr)
            sys.exit(1)
        print(f"BASE_SHA not provided; using fallback: {base_sha}")

    if not head_sha:
        try:
            head_sha = repo.git.rev_parse("HEAD").strip()
        except git.GitCommandError:
            print("Error: Could not determine HEAD_SHA.", file=sys.stderr)
            sys.exit(1)
        print(f"HEAD_SHA not provided; using fallback: {head_sha}")

    try:
        changed_files = repo.git.diff(
            "--name-only", f"{base_sha}...{head_sha}",
        ).strip()
    except git.GitCommandError:
        changed_files = ""

    if not changed_files:
        print(f"No changed files detected between {base_sha} and {head_sha}")
        _set_output("has_changes", "false")
        _set_output("ecosystem", "none")
        _set_output("dependencies", "")
        return

    print("Changed files:")
    print(changed_files)

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

    go_deps = []
    rust_deps = []

    if has_go:
        print("Extracting Go dependency changes...")
        try:
            go_deps = get_go_deps(base_sha, head_sha, repo=repo)
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
            rust_deps = get_rust_deps(base_sha, head_sha, repo=repo)
        except Exception as exc:
            print(f"Warning: Rust dependency extraction failed: {exc}")
        if rust_deps:
            print("Rust dependencies changed:")
            print("\n".join(rust_deps))
        else:
            print("Rust manifest files changed but no individual dependency "
                  "changes detected")

    if has_go and has_rust:
        ecosystem = "mixed"
    elif has_go:
        ecosystem = "go"
    else:
        ecosystem = "rust"

    all_deps = go_deps + rust_deps
    dependencies = ",".join(all_deps)
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
