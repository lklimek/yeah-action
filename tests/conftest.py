"""Shared fixtures for dependency-detection scenario tests.

Uses GitPython for all git operations and pytest for test orchestration.
Each test gets an isolated temporary git repository seeded with the
initial test-projects/ content, so tests never touch the real repo.
"""

import os
import shutil
import sys
from pathlib import Path

import git
import pytest

# Location of the real action root (for scripts and initial test data).
ACTION_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ACTION_ROOT / "scripts"
TEST_PROJECTS_SRC = ACTION_ROOT / "test-projects"

# Ensure the scripts directory is importable.
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


class Scenario:
    """Helper that manages an isolated temporary git repo for a single test."""

    def __init__(self, repo: git.Repo, repo_dir: Path, output_file: Path):
        self.repo = repo
        self.repo_dir = repo_dir
        self.output_file = output_file

    # -- git helpers (via GitPython) ----------------------------------------

    def write_file(self, relpath: str, content: str) -> Path:
        """Write *content* to *relpath* (relative to temp repo root)."""
        full = self.repo_dir / relpath
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
        return full

    def append_file(self, relpath: str, content: str) -> Path:
        """Append *content* to an existing file at *relpath*."""
        full = self.repo_dir / relpath
        with full.open("a") as fh:
            fh.write(content)
        return full

    def commit(self, message: str = "test commit") -> git.Commit:
        """Stage everything under ``test-projects/`` and commit."""
        changed = [
            item.a_path
            for item in self.repo.index.diff(None)
            if item.a_path.startswith("test-projects/")
        ]
        untracked = [
            f for f in self.repo.untracked_files if f.startswith("test-projects/")
        ]
        to_add = changed + untracked
        if to_add:
            self.repo.index.add(to_add)
        return self.repo.index.commit(message)

    @property
    def base_sha(self) -> str:
        """SHA of the commit *before* the test commit (HEAD~1).

        If the HEAD commit has no parents (e.g., initial commit), fall back
        to the HEAD commit's own SHA to avoid IndexError.
        """
        commit = self.repo.head.commit
        if commit.parents:
            return commit.parents[0].hexsha
        return commit.hexsha

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
            "ACTION_PATH": str(ACTION_ROOT),
            "BASE_SHA": self.base_sha,
            "HEAD_SHA": self.head_sha,
        }
        if env_overrides:
            env.update(env_overrides)

        subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "detect_changes.py")],
            env=env,
            cwd=str(self.repo_dir),
            check=True,
        )
        return self._parse_output()

    def run_detect_force(
        self, dependency: str, *, ecosystem: str = "", env_overrides: dict | None = None
    ) -> dict[str, str]:
        """Run ``detect_changes.py`` in force mode."""
        import subprocess

        env = {
            **os.environ,
            "GITHUB_OUTPUT": str(self.output_file),
            "ACTION_PATH": str(ACTION_ROOT),
            "INPUT_DEPENDENCY": dependency,
        }
        if ecosystem:
            env["INPUT_ECOSYSTEM"] = ecosystem
        else:
            env.pop("INPUT_ECOSYSTEM", None)
        if env_overrides:
            env.update(env_overrides)

        subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "detect_changes.py")],
            env=env,
            cwd=str(self.repo_dir),
            check=True,
        )
        return self._parse_output()

    def get_go_deps(self) -> list[str]:
        """Call ``get_go_deps()`` from go_deps.py directly."""
        from go_deps import get_go_deps

        return get_go_deps(self.base_sha, self.head_sha, repo=self.repo)

    def get_rust_deps(self) -> list[str]:
        """Call ``get_rust_deps()`` from rust_deps.py directly."""
        from rust_deps import get_rust_deps

        return get_rust_deps(self.base_sha, self.head_sha, repo=self.repo)

    # -- output parsing -----------------------------------------------------

    def _parse_output(self) -> dict[str, str]:
        result = {}
        for line in self.output_file.read_text().splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                result[key] = value
        return result


@pytest.fixture()
def scenario(tmp_path):
    """Yield a :class:`Scenario` backed by a fresh temporary git repository.

    The temp repo is seeded with the initial test-projects/ content and an
    initial commit, so tests can modify files and create new commits on top.
    """
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    # Initialise a new git repo.
    repo = git.Repo.init(str(repo_dir))
    repo.config_writer().set_value("user", "name", "Test").release()
    repo.config_writer().set_value("user", "email", "test@test.com").release()

    # Seed with initial test-projects/ content.
    dest = repo_dir / "test-projects"
    shutil.copytree(str(TEST_PROJECTS_SRC), str(dest))

    # Create the initial commit.
    repo.index.add(
        [str(p.relative_to(repo_dir)) for p in dest.rglob("*") if p.is_file()]
    )
    repo.index.commit("initial test-projects content")

    output_file = tmp_path / "github_output"
    output_file.touch()

    yield Scenario(repo, repo_dir, output_file)
