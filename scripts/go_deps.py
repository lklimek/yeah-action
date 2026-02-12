#!/usr/bin/env python3
"""
go_deps.py

Extracts Go dependency changes between two Git commits by parsing go.mod
diffs. When go.sum is present and changed, also extracts transitive
dependency changes from it.

Output format (one per line):
    module@old_version..new_version   (version change)
    module@new_version                (new dependency)
    module                            (version unknown)
"""

import re
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


# go.mod requirement line:  +	github.com/lib/pq v1.10.9
_GOMOD_REQ = re.compile(
    r"^\+\s*([-a-zA-Z0-9_.~/]+\.[a-zA-Z]{2,}[-a-zA-Z0-9_.~/]*)\s+(v\S+)"
)

# go.sum entry:  github.com/lib/pq v1.10.9 h1:...
_GOSUM_ENTRY = re.compile(
    r"^\s*([-a-zA-Z0-9_.~/]+\.[a-zA-Z]{2,}[-a-zA-Z0-9_.~/]*)\s+(v[0-9]\S+)"
)


def _deps_from_gomod(base_sha, head_sha, gomod_path):
    """Parse a go.mod diff and return {module: (old_ver, new_ver)}."""
    diff = _run_git("diff", f"{base_sha}...{head_sha}", "--", gomod_path)
    if not diff:
        return {}

    new_modules = {}
    for line in diff.splitlines():
        if line.startswith("+++"):
            continue
        m = _GOMOD_REQ.match(line)
        if m:
            new_modules[m.group(1)] = m.group(2)

    if not new_modules:
        return {}

    # Lookup old versions from the base go.mod.
    base_content = _run_git("show", f"{base_sha}:{gomod_path}")
    results = {}
    for mod, new_ver in new_modules.items():
        old_ver = None
        if base_content:
            pattern = re.compile(
                rf"^\s*{re.escape(mod)}\s+(v\S+)", re.MULTILINE
            )
            hit = pattern.search(base_content)
            if hit:
                old_ver = hit.group(1)
        results[mod] = (old_ver, new_ver)

    return results


def _deps_from_gosum(base_sha, head_sha, gosum_path):
    """Parse a go.sum diff and return {module: (old_ver, new_ver)}.

    Detects added and removed dependency checksums to infer version changes,
    including transitive dependencies not listed in go.mod.
    """
    diff = _run_git("diff", f"{base_sha}...{head_sha}", "--", gosum_path)
    if not diff:
        return {}

    added = {}   # module -> set of versions
    removed = {}  # module -> set of versions

    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue

        is_add = line.startswith("+")
        is_rm = line.startswith("-")
        if not (is_add or is_rm):
            continue

        content = line[1:]

        # Skip /go.mod checksum lines to avoid duplicates.
        if "/go.mod " in content:
            continue

        m = _GOSUM_ENTRY.match(content)
        if not m:
            continue

        mod, ver = m.group(1), m.group(2)
        target = added if is_add else removed
        target.setdefault(mod, set()).add(ver)

    results = {}
    for mod in added:
        new_vers = sorted(added[mod])
        old_vers = sorted(removed.get(mod, set()))
        new_ver = new_vers[-1] if new_vers else None
        old_ver = old_vers[0] if old_vers else None
        if new_ver:
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
