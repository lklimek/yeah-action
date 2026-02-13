#!/usr/bin/env python3
"""Shared Git utility functions for dependency extraction modules."""

import git


def show_file(repo, sha, path):
    """Return file content at a specific commit, or empty string on failure."""
    try:
        return repo.git.show(f"{sha}:{path}")
    except git.GitCommandError:
        return ""


def changed_files(repo, base_sha, head_sha, *patterns):
    """Return list of changed files matching git pathspec patterns."""
    try:
        output = repo.git.diff(
            "--name-only",
            f"{base_sha}...{head_sha}",
            "--",
            *patterns,
        )
        return [f for f in output.splitlines() if f.strip()]
    except git.GitCommandError:
        return []


def format_dep(name, old_ver, new_ver):
    """Format a single dependency change as a string."""
    if old_ver and new_ver and old_ver != new_ver:
        return f"{name}@{old_ver}..{new_ver}"
    elif new_ver:
        return f"{name}@{new_ver}"
    return name
