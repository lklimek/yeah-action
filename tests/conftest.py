"""Shared fixtures for dependency-detection scenario tests.

Uses GitPython for all git operations and pytest for test orchestration.
"""

import os
import sys
import tempfile
from pathlib import Path

import git
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Ensure the scripts directory is importable.
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


class Scenario:
    """Helper that manages a throwaway git branch for a single test."""

    def __init__(self, repo: git.Repo, branch_name: str, output_file: Path):
        self.repo = repo
        self.branch_name = branch_name
        self.output_file = output_file

    # -- git helpers (via GitPython) ----------------------------------------

    def write_file(self, relpath: str, content: str) -> Path:
        """Write *content* to *relpath* (relative to repo root)."""
        full = REPO_ROOT / relpath
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
        return full

    def append_file(self, relpath: str, content: str) -> Path:
        """Append *content* to an existing file at *relpath*."""
        full = REPO_ROOT / relpath
        with full.open("a") as fh:
            fh.write(content)
        return full

    def commit(self, message: str = "test commit") -> git.Commit:
        """Stage everything under ``test-projects/`` and commit."""
        # Use repo.index to add only test-projects/ changes.
        # We need to collect actual changed/new files under test-projects/.
        test_dir = str(REPO_ROOT / "test-projects")
        changed = [
            item.a_path
            for item in self.repo.index.diff(None)
            if item.a_path.startswith("test-projects/")
        ]
        untracked = [
            f for f in self.repo.untracked_files
            if f.startswith("test-projects/")
        ]
        to_add = changed + untracked
        if to_add:
            self.repo.index.add(to_add)
        return self.repo.index.commit(message)

    @property
    def base_sha(self) -> str:
        """SHA of the commit *before* the test commit (HEAD~1)."""
        return self.repo.head.commit.parents[0].hexsha

    @property
    def head_sha(self) -> str:
        """SHA of the current HEAD."""
        return self.repo.head.commit.hexsha

    # -- script runners -----------------------------------------------------

    def run_detect(self, *, env_overrides: dict | None = None) -> dict[str, str]:
        """Run ``detect_changes.py`` and return parsed GITHUB_OUTPUT dict."""
        import subprocess

        env = {
            **os.environ,
            "GITHUB_OUTPUT": str(self.output_file),
            "ACTION_PATH": str(REPO_ROOT),
            "BASE_SHA": self.base_sha,
            "HEAD_SHA": self.head_sha,
        }
        if env_overrides:
            env.update(env_overrides)

        subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "detect_changes.py")],
            env=env,
            check=True,
        )
        return self._parse_output()

    def run_detect_force(self, dependency: str, *,
                         ecosystem: str = "",
                         env_overrides: dict | None = None) -> dict[str, str]:
        """Run ``detect_changes.py`` in force mode."""
        import subprocess

        env = {
            **os.environ,
            "GITHUB_OUTPUT": str(self.output_file),
            "ACTION_PATH": str(REPO_ROOT),
            "INPUT_DEPENDENCY": dependency,
        }
        if ecosystem:
            env["INPUT_ECOSYSTEM"] = ecosystem
        else:
            env.pop("INPUT_ECOSYSTEM", None)
        # Remove stale env vars that might interfere.
        env.pop("INPUT_DEPENDENCY", None)
        env["INPUT_DEPENDENCY"] = dependency
        if env_overrides:
            env.update(env_overrides)

        subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "detect_changes.py")],
            env=env,
            check=True,
        )
        return self._parse_output()

    def get_go_deps(self) -> list[str]:
        """Call ``get_go_deps()`` from go_deps.py directly."""
        from go_deps import get_go_deps
        return get_go_deps(self.base_sha, self.head_sha)

    def get_rust_deps(self) -> list[str]:
        """Call ``get_rust_deps()`` from rust_deps.py directly."""
        from rust_deps import get_rust_deps
        return get_rust_deps(self.base_sha, self.head_sha)

    # -- output parsing -----------------------------------------------------

    def _parse_output(self) -> dict[str, str]:
        result = {}
        for line in self.output_file.read_text().splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                result[key] = value
        return result


@pytest.fixture()
def scenario(request, tmp_path):
    """Yield a :class:`Scenario` with a temporary git branch.

    On teardown the original branch is restored and the test branch deleted.
    """
    repo = git.Repo(str(REPO_ROOT))
    original_branch = repo.active_branch

    branch_name = f"test/{request.node.name}-{os.getpid()}"
    test_branch = repo.create_head(branch_name)
    test_branch.checkout()

    output_file = tmp_path / "github_output"
    output_file.touch()

    ctx = Scenario(repo, branch_name, output_file)

    yield ctx

    # Teardown: restore original branch, delete test branch.
    original_branch.checkout(force=True)
    repo.delete_head(branch_name, force=True)
