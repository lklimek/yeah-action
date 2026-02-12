#!/usr/bin/env bash
set -euo pipefail

# go-deps.sh
#
# Provides the extract_go_deps() function for detecting Go dependency changes
# between two Git commits. Parses go.mod diffs to identify added, removed, or
# updated module requirements, including version transition information.

# extract_go_deps BASE_SHA HEAD_SHA
#
# Diffs go.mod between the two SHAs and extracts changed module paths with
# version information. Output format per line:
#   module@old_version..new_version   (for version changes)
#   module@new_version                (for newly added dependencies)
#   module                            (if version extraction fails)
extract_go_deps() {
  local base_sha="${1:?Missing base_sha argument}"
  local head_sha="${2:?Missing head_sha argument}"

  # Get the diff of go.mod between the two commits.
  # The three-dot diff shows changes introduced on the head branch since it
  # diverged from the base branch.
  local diff_output
  diff_output="$(git diff "${base_sha}...${head_sha}" -- go.mod 2>/dev/null || true)"

  # If there is no diff (go.mod unchanged or does not exist), return nothing.
  if [[ -z "${diff_output}" ]]; then
    return 0
  fi

  # Collect module paths from added lines in the diff.
  # Added lines start with "+" but we skip the "+++ b/go.mod" header line.
  # Go module require lines look like:
  #   +	github.com/lib/pq v1.10.9
  #   +	golang.org/x/text v0.14.0
  # We match lines that have a module path followed by a version (vX.Y.Z...).
  local modules=()
  while IFS= read -r line; do
    # Skip the diff header line.
    if [[ "${line}" == "+++"* ]]; then
      continue
    fi

    # Match added lines that look like Go module requirements.
    # Strip the leading "+" and any whitespace, then look for a module path
    # followed by a version string.
    if [[ "${line}" =~ ^\+[[:space:]]*([-a-zA-Z0-9_.~/]+\.[a-zA-Z]{2,}[-a-zA-Z0-9_.~/]*)[[:space:]]+(v[0-9][^ ]*) ]]; then
      local module_path="${BASH_REMATCH[1]}"
      local new_version="${BASH_REMATCH[2]}"
      modules+=("${module_path}|${new_version}")
    fi
  done <<< "${diff_output}"

  # For each changed module, try to find the old version from the base SHA's
  # go.mod to produce "module@old..new" output.
  for entry in "${modules[@]}"; do
    local module_path="${entry%%|*}"
    local new_version="${entry##*|}"

    # Try to read the base SHA's go.mod to find the old version of this module.
    local old_version=""
    local base_gomod
    base_gomod="$(git show "${base_sha}:go.mod" 2>/dev/null || true)"

    if [[ -n "${base_gomod}" ]]; then
      # Search for the module in the old go.mod. The line format is:
      #   <module_path> <version>
      # We use a grep with word boundary to avoid partial matches.
      local old_line
      old_line="$(echo "${base_gomod}" | grep -E "^[[:space:]]*${module_path//./\\.}[[:space:]]" 2>/dev/null || true)"

      if [[ -n "${old_line}" ]]; then
        # Extract the version from the matched line.
        if [[ "${old_line}" =~ (v[0-9][^ ]*) ]]; then
          old_version="${BASH_REMATCH[1]}"
        fi
      fi
    fi

    # Format the output depending on whether we found an old version.
    if [[ -n "${old_version}" && "${old_version}" != "${new_version}" ]]; then
      # Version was changed (upgrade or downgrade).
      echo "${module_path}@${old_version}..${new_version}"
    elif [[ -n "${new_version}" ]]; then
      # New dependency (not present in base) or version unchanged but line
      # was reformatted.
      echo "${module_path}@${new_version}"
    else
      # Fallback: just the module path if version extraction failed.
      echo "${module_path}"
    fi
  done
}
