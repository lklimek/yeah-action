#!/usr/bin/env python3
"""
rust_deps.py

Extracts Rust crate dependency changes between two Git commits by comparing
Cargo.toml and Cargo.lock files at each commit using TOML parsing and
GitPython for all repository operations.

Output format (one per line):
    crate@old_version..new_version   (version change)
    crate@new_version                (new dependency)
    crate                            (version unknown)
"""

import os
import sys

import git

try:
    import tomllib
except ImportError:
    import tomli as tomllib

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from git_utils import show_file, changed_files, format_dep  # noqa: E402


def _versions_from_toml(content):
    """Parse a Cargo.toml string and return {crate_name: version_or_None}.

    Extracts dependency versions from all dependency sections:
    [dependencies], [dev-dependencies], [build-dependencies],
    [workspace.dependencies], and [target.*.dependencies].
    """
    if not content:
        return {}

    versions = {}
    try:
        parsed = tomllib.loads(content)
    except Exception as exc:
        print(f"Warning: Failed to parse Cargo.toml: {exc}", file=sys.stderr)
        return versions

    dep_keys = ("dependencies", "dev-dependencies", "build-dependencies")

    for key in dep_keys:
        for name, val in parsed.get(key, {}).items():
            if isinstance(val, str):
                versions[name] = val
            elif isinstance(val, dict):
                versions[name] = val.get("version")

    # workspace.dependencies
    for name, val in parsed.get("workspace", {}).get("dependencies", {}).items():
        if isinstance(val, str):
            versions[name] = val
        elif isinstance(val, dict):
            versions[name] = val.get("version")

    # target-specific dependencies
    for _target, cfg in parsed.get("target", {}).items():
        if not isinstance(cfg, dict):
            continue
        for key in dep_keys:
            for name, val in cfg.get(key, {}).items():
                if isinstance(val, str):
                    versions[name] = val
                elif isinstance(val, dict):
                    versions[name] = val.get("version")

    return versions


def _deps_from_cargo_toml(repo, base_sha, head_sha, cargo_path):
    """Compare old/new Cargo.toml and return {crate: (old_ver, new_ver)}."""
    old_content = show_file(repo, base_sha, cargo_path)
    new_content = show_file(repo, head_sha, cargo_path)

    old_versions = _versions_from_toml(old_content)
    new_versions = _versions_from_toml(new_content)

    results = {}
    for name, new_ver in new_versions.items():
        if name not in old_versions or old_versions[name] != new_ver:
            results[name] = (old_versions.get(name), new_ver)

    return results


def _parse_lock(content):
    """Parse a Cargo.lock string and return {package_name: set(versions)}."""
    if not content:
        return {}

    pkgs = {}
    try:
        parsed = tomllib.loads(content)
        for pkg in parsed.get("package", []):
            name = pkg.get("name", "")
            ver = pkg.get("version", "")
            if name and ver:
                pkgs.setdefault(name, set()).add(ver)
    except Exception as exc:
        print(f"Warning: Failed to parse Cargo.lock: {exc}", file=sys.stderr)
    return pkgs


def _deps_from_cargo_lock(repo, base_sha, head_sha, lock_path):
    """Compare old/new Cargo.lock and return {crate: (old_ver, new_ver)}."""
    old_content = show_file(repo, base_sha, lock_path)
    new_content = show_file(repo, head_sha, lock_path)
    old_pkgs = _parse_lock(old_content)
    new_pkgs = _parse_lock(new_content)
    results = {}
    for name, new_versions in new_pkgs.items():
        old_versions = old_pkgs.get(name, set())
        added = new_versions - old_versions
        removed = old_versions - new_versions
        if added:
            new_ver = sorted(added)[-1]
            old_ver = sorted(removed)[0] if removed else None
            results[name] = (old_ver, new_ver)
    return results


def get_rust_deps(base_sha, head_sha, repo=None):
    """Return list of Rust dependency change strings between two commits.

    Parameters
    ----------
    base_sha : str
        Base commit SHA.
    head_sha : str
        Head commit SHA.
    repo : git.Repo, optional
        GitPython Repo instance. Auto-detected from cwd if not provided.
    """
    if repo is None:
        repo = git.Repo(".", search_parent_directories=True)

    toml_files = changed_files(
        repo,
        base_sha,
        head_sha,
        "**/Cargo.toml",
        "Cargo.toml",
    )
    lock_files = changed_files(
        repo,
        base_sha,
        head_sha,
        "**/Cargo.lock",
        "Cargo.lock",
    )

    # Cargo.lock first (lower priority), then Cargo.toml overwrites.
    deps = {}
    for path in lock_files:
        deps.update(_deps_from_cargo_lock(repo, base_sha, head_sha, path))
    for path in toml_files:
        deps.update(_deps_from_cargo_toml(repo, base_sha, head_sha, path))

    return [format_dep(c, old, new) for c, (old, new) in deps.items()]


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} BASE_SHA HEAD_SHA", file=sys.stderr)
        sys.exit(1)
    for line in get_rust_deps(sys.argv[1], sys.argv[2]):
        print(line)
