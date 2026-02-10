#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESULTS_DIR="$(mktemp -d)"
PROJECT_PATH_INPUT="${INPUT_PROJECT_PATH:-.}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
PROJECT_PATH="$(realpath -m "$REPO_ROOT/$PROJECT_PATH_INPUT")"
PROJECT_RELATIVE_PATH="$(realpath --relative-to="$REPO_ROOT" "$PROJECT_PATH")"

cleanup() {
  rm -rf "$RESULTS_DIR"
}
trap cleanup EXIT

if [ ! -d "$PROJECT_PATH" ]; then
  echo "Project path does not exist: $PROJECT_PATH_INPUT"
  exit 1
fi

export YEAH_PROJECT_PATH="$PROJECT_RELATIVE_PATH"
pushd "$PROJECT_PATH" >/dev/null

echo "::group::🦀 YEAH — Detecting dependency changes"
python3 "$SCRIPT_DIR/parse-lockfile.py" > "$RESULTS_DIR/changes.json"
echo "::endgroup::"

CHANGE_COUNT=$(jq '.changes | length' "$RESULTS_DIR/changes.json")
if [ "$CHANGE_COUNT" -eq 0 ]; then
  echo "YEAH! No dependency changes detected. Nothing to review."
  exit 0
fi

echo "::group::Generating crate diffs"
bash "$SCRIPT_DIR/generate-diffs.sh" "$RESULTS_DIR"
echo "::endgroup::"

echo "::group::Running security tools"
bash "$SCRIPT_DIR/run-security.sh" "$RESULTS_DIR"
echo "::endgroup::"

echo "::group::AI security review"
bash "$SCRIPT_DIR/ai-review.sh" "$RESULTS_DIR"
echo "::endgroup::"

echo "::group::Posting results"
bash "$SCRIPT_DIR/post-comment.sh" "$RESULTS_DIR"
echo "::endgroup::"

popd >/dev/null
