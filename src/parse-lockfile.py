#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from typing import Dict, Iterable, Set

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - fallback for older runtimes
    import tomli as tomllib  # type: ignore


def load_lockfile(contents: str) -> Dict[str, Set[str]]:
    data = tomllib.loads(contents)
    packages = data.get("package", [])
    result: Dict[str, Set[str]] = {}
    for package in packages:
        name = package.get("name")
        version = package.get("version")
        if not name or not version:
            continue
        result.setdefault(name, set()).add(str(version))
    return result


def load_file(path: str) -> str:
    with open(path, "rb") as handle:
        return handle.read().decode("utf-8", errors="replace")


def read_base_lockfile() -> str | None:
    base_ref = os.environ.get("GITHUB_BASE_REF")
    if not base_ref:
        return None
    project_path = os.environ.get("YEAH_PROJECT_PATH", ".").strip()
    lockfile_path = "Cargo.lock"
    if project_path not in ("", "."):
        lockfile_path = f"{project_path.rstrip('/')}/Cargo.lock"
    result = subprocess.run(
        ["git", "show", f"origin/{base_ref}:{lockfile_path}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def stringify_versions(versions: Iterable[str]) -> str | None:
    versions_list = sorted(versions)
    if not versions_list:
        return None
    return ",".join(versions_list)


def main() -> int:
    if not os.path.exists("Cargo.lock"):
        print(
            json.dumps({"changes": []}, indent=2),
            file=sys.stdout,
        )
        print("Cargo.lock not found; skipping dependency diff.", file=sys.stderr)
        return 0

    new_contents = load_file("Cargo.lock")
    base_contents = read_base_lockfile()

    new_packages = load_lockfile(new_contents)
    old_packages = load_lockfile(base_contents) if base_contents else {}

    changes = []
    for name in sorted(set(old_packages) | set(new_packages)):
        old_versions = old_packages.get(name, set())
        new_versions = new_packages.get(name, set())
        if old_versions == new_versions:
            continue
        old_value = stringify_versions(old_versions)
        new_value = stringify_versions(new_versions)
        if not old_versions:
            change_type = "added"
        elif not new_versions:
            change_type = "removed"
        else:
            change_type = "updated"
        changes.append(
            {
                "crate": name,
                "old": old_value,
                "new": new_value,
                "type": change_type,
            }
        )

    print(json.dumps({"changes": changes}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
