#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

from tooling import ensure_tool


def run_to_file(args: list[str], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as handle:
        subprocess.run(args, stdout=handle, stderr=subprocess.STDOUT)


def is_enabled(env_var: str) -> bool:
    return os.getenv(env_var, "true").lower() == "true"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: run-security.py <results_dir>")
        return 1

    results_dir = Path(sys.argv[1])

    if is_enabled("INPUT_CARGO_AUDIT"):
        print("Running cargo audit...")
        ensure_tool("cargo audit --version", "cargo-audit")
        run_to_file(["cargo", "audit", "--json"], results_dir / "audit.json")

    if is_enabled("INPUT_CARGO_DENY"):
        print("Running cargo deny...")
        ensure_tool("cargo deny --version", "cargo-deny")
        run_to_file(["cargo", "deny", "check"], results_dir / "deny.txt")

    if is_enabled("INPUT_CARGO_VET"):
        print("Running cargo vet...")
        ensure_tool("cargo vet --version", "cargo-vet")
        run_to_file(["cargo", "vet", "--output-format=json"], results_dir / "vet.json")

    if is_enabled("INPUT_CARGO_GEIGER"):
        print("Running cargo geiger...")
        ensure_tool("cargo geiger --version", "cargo-geiger")
        run_to_file(
            ["cargo", "geiger", "--output-format", "json", "--quiet"],
            results_dir / "geiger.json",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
