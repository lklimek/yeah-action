#!/usr/bin/env python3
"""
go_deps.py

Extracts Go dependency changes between two Git commits by comparing go.mod
and go.sum files at each commit. Uses structured parsing of both formats
rather than regex-based diff scraping.

Output format (one per line):
    module@old_version..new_version   (version change)
    module@new_version                (new dependency)
    module                            (version unknown)
"""

import subprocess
import sys


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


def _changed_files(base_sha, head_sha, *patterns):
    """Return list of changed files matching git pathspec patterns."""
    args = ["diff", "--name-only", f"{base_sha}...{head_sha}", "--"]
    args.extend(patterns)
    output = _run_git(*args)
    return [f for f in output.splitlines() if f.strip()]


def _parse_gomod(content):
    """Parse go.mod content and return {module_path: version}.

    Handles both single-line and block require directives:
        require github.com/lib/pq v1.10.9
        require (
            github.com/lib/pq v1.10.9
            golang.org/x/text v0.14.0 // indirect
        )
    """
    if not content:
        return {}

    deps = {}
    in_require = False

    for line in content.splitlines():
        stripped = line.strip()

        if not stripped or stripped.startswith("//"):
            continue

        if stripped == ")":
            in_require = False
            continue

        if stripped.startswith("require ("):
            in_require = True
            continue

        if stripped.startswith("require ") and not in_require:
            # Single-line: require <module> <version> [// comment]
            parts = stripped.split()
            if len(parts) >= 3 and parts[2].startswith("v"):
                deps[parts[1]] = parts[2]
            continue

        if in_require:
            # Block entry: <module> <version> [// comment]
            parts = stripped.split()
            if len(parts) >= 2 and parts[1].startswith("v"):
                deps[parts[0]] = parts[1]

    return deps


def _parse_gosum(content):
    """Parse go.sum content and return {module: set(versions)}.

    go.sum lines have the format:
        module version h1:hash=
        module version/go.mod h1:hash=
    Entries with /go.mod suffix are skipped to avoid duplicates.
    """
    if not content:
        return {}

    deps = {}
    for line in content.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue

        module, version = parts[0], parts[1]

        # Skip /go.mod checksum entries.
        if version.endswith("/go.mod"):
            continue

        deps.setdefault(module, set()).add(version)

    return deps


def _deps_from_gomod(base_sha, head_sha, gomod_path):
    """Compare old/new go.mod and return {module: (old_ver, new_ver)}."""
    old_content = _run_git("show", f"{base_sha}:{gomod_path}")
    new_content = _run_git("show", f"{head_sha}:{gomod_path}")

    old_deps = _parse_gomod(old_content)
    new_deps = _parse_gomod(new_content)

    results = {}
    for mod, new_ver in new_deps.items():
        if mod not in old_deps or old_deps[mod] != new_ver:
            results[mod] = (old_deps.get(mod), new_ver)

    return results


def _deps_from_gosum(base_sha, head_sha, gosum_path):
    """Compare old/new go.sum and return {module: (old_ver, new_ver)}.

    Detects transitive dependency changes not listed in go.mod.
    """
    old_content = _run_git("show", f"{base_sha}:{gosum_path}")
    new_content = _run_git("show", f"{head_sha}:{gosum_path}")

    old_sums = _parse_gosum(old_content)
    new_sums = _parse_gosum(new_content)

    results = {}
    for mod, new_versions in new_sums.items():
        old_versions = old_sums.get(mod, set())
        added = new_versions - old_versions
        removed = old_versions - new_versions

        if added:
            new_ver = sorted(added)[-1]
            old_ver = sorted(removed)[0] if removed else None
            results[mod] = (old_ver, new_ver)

    return results


def _format_dep(name, old_ver, new_ver):
    """Format a single dependency change as a string."""
    if old_ver and new_ver and old_ver != new_ver:
        return f"{name}@{old_ver}..{new_ver}"
    elif new_ver:
        return f"{name}@{new_ver}"
    return name


def get_go_deps(base_sha, head_sha):
    """Return list of Go dependency change strings between two commits."""
    gomod_files = _changed_files(base_sha, head_sha, "**/go.mod", "go.mod")
    gosum_files = _changed_files(base_sha, head_sha, "**/go.sum", "go.sum")

    # go.sum first (lower priority), then go.mod overwrites for direct deps.
    deps = {}
    for path in gosum_files:
        deps.update(_deps_from_gosum(base_sha, head_sha, path))
    for path in gomod_files:
        deps.update(_deps_from_gomod(base_sha, head_sha, path))

    return [_format_dep(mod, old, new) for mod, (old, new) in deps.items()]


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} BASE_SHA HEAD_SHA", file=sys.stderr)
        sys.exit(1)
    for line in get_go_deps(sys.argv[1], sys.argv[2]):
        print(line)
