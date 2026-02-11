#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run_group(title: str, func) -> None:
    print(f"::group::{title}")
    try:
        func()
    finally:
        print("::endgroup::")


def run_script(script_path: Path, results_dir: Path) -> None:
    subprocess.run(
        [sys.executable, str(script_path), str(results_dir)],
        check=True,
    )


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    results_dir = Path(tempfile.mkdtemp())
    project_input = os.getenv("INPUT_PROJECT_PATH", ".")

    try:
        repo_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
        project_path = Path(repo_root, project_input).resolve()
        if not project_path.is_dir():
            print(f"Project path does not exist: {project_input}")
            return 1

        project_relative = os.path.relpath(project_path, repo_root)
        os.environ["YEAH_PROJECT_RELATIVE_PATH"] = project_relative
        os.chdir(project_path)

        changes_path = results_dir / "changes.json"

        def detect_changes() -> None:
            with changes_path.open("w", encoding="utf-8") as handle:
                subprocess.run(
                    [sys.executable, str(script_dir / "parse-lockfile.py")],
                    stdout=handle,
                    check=True,
                )

        run_group("🦀 YEAH — Detecting dependency changes", detect_changes)

        with changes_path.open("r", encoding="utf-8") as handle:
            changes_payload = json.load(handle)

        if not changes_payload.get("changes"):
            print("YEAH! No dependency changes detected. Nothing to review.")
            return 0

        run_group(
            "Generating crate diffs",
            lambda: run_script(script_dir / "generate-diffs.py", results_dir),
        )
        run_group(
            "Running security tools",
            lambda: run_script(script_dir / "run-security.py", results_dir),
        )
        run_group(
            "AI security review",
            lambda: run_script(script_dir / "ai-review.py", results_dir),
        )
        run_group(
            "Posting results",
            lambda: run_script(script_dir / "post-comment.py", results_dir),
        )
    finally:
        shutil.rmtree(results_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
