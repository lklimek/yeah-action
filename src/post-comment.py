#!/usr/bin/env python3
import json
import os
import sys
import urllib.request
from pathlib import Path

MARKER = "<!-- yeah-action-review -->"
HEADER = "## 🦀 YEAH — Supply Chain Review"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def code_block(language: str, content: str) -> list[str]:
    lines = [f"```{language}"]
    lines.extend(content.splitlines())
    lines.append("```")
    return lines


def github_request(method: str, url: str, token: str, body: dict | None = None):
    headers = {
        "accept": "application/vnd.github+json",
        "authorization": f"Bearer {token}",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request) as response:
        if response.status == 204:
            return None
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: post-comment.py <results_dir>")
        return 1

    results_dir = Path(sys.argv[1])
    pr_number = os.getenv("PR_NUMBER")
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    if not pr_number or not token or not repo:
        print("PR_NUMBER, GITHUB_TOKEN, or GITHUB_REPOSITORY not set; skipping comment posting.")
        return 0

    lines = [HEADER, MARKER, "", "### Dependency changes"]
    changes_path = results_dir / "changes.json"
    if changes_path.exists():
        changes = read_json(changes_path).get("changes", [])
        for change in changes:
            old = change.get("old") or "none"
            new = change.get("new") or "none"
            lines.append(f"- {change.get('crate')}: {old} -> {new} ({change.get('type')})")
    else:
        lines.append("No dependency change data available.")

    lines.append("")
    lines.append("### Diff generation")
    diffs_path = results_dir / "diffs.json"
    if diffs_path.exists():
        diffs_payload = read_json(diffs_path)
        if diffs_payload.get("skipped"):
            reason = diffs_payload.get("reason") or "unknown"
            lines.append(f"Diffs skipped: {reason}")
        else:
            for diff in diffs_payload.get("diffs", []):
                note = diff.get("note") or ""
                lines.append(f"- {diff.get('crate')}: {diff.get('status')} {note}".rstrip())
    else:
        lines.append("Diff results not available.")

    def add_tool_section(title: str, filename: str, language: str) -> None:
        lines.append("")
        lines.append(f"### {title}")
        path = results_dir / filename
        if path.exists():
            lines.append("<details>")
            lines.append(f"<summary>View {title.lower()} output</summary>")
            lines.append("")
            lines.extend(code_block(language, path.read_text(encoding="utf-8")))
            lines.append("</details>")
        else:
            lines.append("Not run.")

    add_tool_section("Cargo audit", "audit.json", "json")
    add_tool_section("Cargo deny", "deny.txt", "text")
    add_tool_section("Cargo vet", "vet.json", "json")
    add_tool_section("Cargo geiger", "geiger.json", "json")

    lines.append("")
    lines.append("### AI security review")
    ai_path = results_dir / "ai-review.md"
    if ai_path.exists():
        lines.extend(ai_path.read_text(encoding="utf-8").splitlines())
    else:
        lines.append("Not run.")

    comment_body = "\n".join(lines).rstrip() + "\n"
    api_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    mode = os.getenv("INPUT_COMMENT_MODE", "update")

    comment_id = None
    if mode == "update":
        existing = github_request("GET", f"{api_url}?per_page=100", token) or []
        for entry in existing:
            if MARKER in entry.get("body", ""):
                comment_id = entry.get("id")
                break

    if comment_id:
        github_request(
            "PATCH",
            f"https://api.github.com/repos/{repo}/issues/comments/{comment_id}",
            token,
            {"body": comment_body},
        )
    else:
        github_request("POST", api_url, token, {"body": comment_body})

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
