#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

from tooling import ensure_tool


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: generate-diffs.py <results_dir>")
        return 1

    results_dir = Path(sys.argv[1])
    changes_file = results_dir / "changes.json"
    diff_dir = results_dir / "diffs"
    diff_dir.mkdir(parents=True, exist_ok=True)

    if os.getenv("INPUT_CARGO_VET", "true").lower() != "true":
        write_json(
            results_dir / "diffs.json",
            {"skipped": True, "reason": "cargo vet disabled", "diffs": []},
        )
        return 0

    if not Path("supply-chain/config.toml").exists() and not Path(
        "supply-chain/audits.toml"
    ).exists():
        write_json(
            results_dir / "diffs.json",
            {"skipped": True, "reason": "cargo vet not initialized", "diffs": []},
        )
        return 0

    ensure_tool("cargo vet --version", "cargo-vet")

    max_diff_size = int(os.getenv("INPUT_MAX_DIFF_SIZE", "50000"))
    changes_payload = json.loads(changes_file.read_text(encoding="utf-8"))
    diffs = []

    for change in changes_payload.get("changes", []):
        crate = change.get("crate")
        old = change.get("old")
        new = change.get("new")
        change_type = change.get("type")

        status = "skipped"
        note = ""
        diff_path = ""
        truncated = False

        if change_type == "updated":
            if (old and "," in old) or (new and "," in new):
                note = "multiple versions changed"
            elif old and new:
                safe_name = crate.replace("/", "_").replace(" ", "_")
                diff_file = diff_dir / f"{safe_name}-{old}-to-{new}.diff"
                with diff_file.open("w", encoding="utf-8") as handle:
                    result = subprocess.run(
                        ["cargo", "vet", "diff", crate, old, new],
                        stdout=handle,
                        stderr=subprocess.STDOUT,
                    )
                if result.returncode == 0:
                    status = "ok"
                else:
                    status = "error"
                    note = "cargo vet diff failed"

                if diff_file.exists():
                    diff_size = diff_file.stat().st_size
                    if diff_size > max_diff_size:
                        with diff_file.open("rb") as handle:
                            content = handle.read(max_diff_size)
                        diff_file.write_bytes(content)
                        truncated = True
                    diff_path = f"diffs/{diff_file.name}"
            else:
                note = "version information missing"
        else:
            note = f"crate was {change_type}"

        diffs.append(
            {
                "crate": crate,
                "old": old,
                "new": new,
                "status": status,
                "note": note,
                "path": diff_path,
                "truncated": truncated,
            }
        )

    write_json(results_dir / "diffs.json", {"skipped": False, "reason": None, "diffs": diffs})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
