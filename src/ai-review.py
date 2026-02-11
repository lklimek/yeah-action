#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_ai_response(url: str, headers: dict, body: dict) -> str:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.read().decode("utf-8")
    except Exception:
        return ""


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: ai-review.py <results_dir>")
        return 1

    results_dir = Path(sys.argv[1])
    script_dir = Path(__file__).resolve().parent
    prompt_file = script_dir.parent / "prompts" / "security-review.md"
    review_input = results_dir / "review-input.txt"
    ai_output = results_dir / "ai-review.md"
    model = os.getenv("INPUT_MODEL", "claude-sonnet-4-20250514")

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")

    if not anthropic_key and not openai_key:
        ai_output.write_text("AI review skipped: no API key provided.", encoding="utf-8")
        return 0

    lines: list[str] = [prompt_file.read_text(encoding="utf-8").rstrip(), "", "## Dependency changes"]
    changes_payload = read_json(results_dir / "changes.json")
    for change in changes_payload.get("changes", []):
        old = change.get("old") or "none"
        new = change.get("new") or "none"
        lines.append(f"- {change.get('crate')}: {old} -> {new} ({change.get('type')})")

    lines.append("")

    diffs_path = results_dir / "diffs.json"
    if diffs_path.exists():
        diffs_payload = read_json(diffs_path)
        if diffs_payload.get("skipped"):
            reason = diffs_payload.get("reason") or "unknown"
            lines.append(f"Diffs skipped: {reason}")
        else:
            for diff in diffs_payload.get("diffs", []):
                if diff.get("status") != "ok":
                    continue
                path = diff.get("path")
                if not path:
                    continue
                diff_file = results_dir / path
                if not diff_file.exists():
                    continue
                old = diff.get("old") or "unknown"
                new = diff.get("new") or "unknown"
                lines.append("")
                lines.append(f"### Diff for {diff.get('crate')} ({old} -> {new})")
                lines.append("```diff")
                lines.extend(diff_file.read_text(encoding="utf-8").splitlines())
                lines.append("```")

    review_text = "\n".join(lines).rstrip() + "\n"
    review_input.write_text(review_text, encoding="utf-8")

    request_body = {
        "model": model,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": review_text}],
    }

    if anthropic_key:
        response_text = fetch_ai_response(
            "https://api.anthropic.com/v1/messages",
            {
                "content-type": "application/json",
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
            },
            request_body,
        )
        try:
            payload = json.loads(response_text)
            ai_text = payload.get("content", [{}])[0].get("text", "")
        except json.JSONDecodeError:
            ai_text = ""
    else:
        response_text = fetch_ai_response(
            "https://api.openai.com/v1/chat/completions",
            {
                "content-type": "application/json",
                "authorization": f"Bearer {openai_key}",
            },
            request_body,
        )
        try:
            payload = json.loads(response_text)
            ai_text = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
        except json.JSONDecodeError:
            ai_text = ""

    if not ai_text:
        ai_output.write_text("AI review failed to produce output.", encoding="utf-8")
    else:
        ai_output.write_text(ai_text.strip() + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
