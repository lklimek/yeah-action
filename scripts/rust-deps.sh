#!/usr/bin/env bash
set -euo pipefail

# rust-deps.sh
#
# Provides the extract_rust_deps() function for detecting Rust dependency
# changes between two Git commits. Parses Cargo.toml diffs to identify added
# or updated crate dependencies, including version transition information.

# extract_rust_deps BASE_SHA HEAD_SHA
#
# Diffs Cargo.toml between the two SHAs and extracts changed crate names with
# version information. Handles both inline and table dependency formats:
#   crate_name = "1.0"
#   crate_name = { version = "1.0", features = [...] }
#
# Output format per line:
#   crate@old_version..new_version   (for version changes)
#   crate@new_version                (for newly added dependencies)
#   crate                            (if version extraction fails)
extract_rust_deps() {
  local base_sha="${1:?Missing base_sha argument}"
  local head_sha="${2:?Missing head_sha argument}"

  # Find all changed Cargo.toml files (root and subdirectories).
  local changed_cargo_files
  changed_cargo_files="$(git diff --name-only "${base_sha}...${head_sha}" -- '**/Cargo.toml' 'Cargo.toml' 2>/dev/null || true)"

  if [[ -z "${changed_cargo_files}" ]]; then
    return 0
  fi

  # Process each changed Cargo.toml file.
  while IFS= read -r cargo_file; do
    [[ -z "${cargo_file}" ]] && continue
    _extract_rust_deps_from_file "${base_sha}" "${head_sha}" "${cargo_file}"
  done <<< "${changed_cargo_files}"
}

# _extract_rust_deps_from_file BASE_SHA HEAD_SHA CARGO_TOML_PATH
#
# Internal helper: extracts changed dependencies from a single Cargo.toml file.
_extract_rust_deps_from_file() {
  local base_sha="${1}"
  local head_sha="${2}"
  local cargo_file="${3}"

  # Get the diff of this specific Cargo.toml between the two commits.
  local diff_output
  diff_output="$(git diff "${base_sha}...${head_sha}" -- "${cargo_file}" 2>/dev/null || true)"

  # If there is no diff, return nothing.
  if [[ -z "${diff_output}" ]]; then
    return 0
  fi

  # Track whether we are inside a dependency section.
  # Cargo.toml dependency sections are:
  #   [dependencies]
  #   [dev-dependencies]
  #   [build-dependencies]
  #   [workspace.dependencies]
  # We also handle target-specific dependencies like:
  #   [target.'cfg(...)'.dependencies]
  local in_dep_section=false
  local crates=()

  while IFS= read -r line; do
    # Skip diff header lines.
    if [[ "${line}" == "+++"* || "${line}" == "---"* ]]; then
      continue
    fi

    # Strip the leading diff marker (+, -, or space) for section detection.
    local content="${line#[+ -]}"

    # Detect section headers to know when we are in a dependency section.
    # Section headers look like [dependencies], [dev-dependencies], etc.
    if [[ "${content}" =~ ^\[([a-zA-Z._\'-]+)\] ]] || [[ "${content}" =~ ^\[([a-zA-Z._\'-]+)\]$ ]]; then
      local section="${BASH_REMATCH[1]}"
      # Check if this section is a dependency section.
      if [[ "${section}" =~ dependencies ]] || [[ "${section}" =~ Dependencies ]]; then
        in_dep_section=true
      else
        in_dep_section=false
      fi
      continue
    fi

    # Also detect more complex section headers like [target.'cfg(...)'.dependencies].
    if [[ "${content}" =~ ^\[.*dependencies.*\]$ ]]; then
      in_dep_section=true
      continue
    fi

    # If a new section starts that is not a dependency section, stop tracking.
    if [[ "${content}" =~ ^\[ ]]; then
      in_dep_section=false
      continue
    fi

    # Only process added lines (starting with "+") inside dependency sections.
    if [[ "${line}" != "+"* ]] || [[ "${in_dep_section}" != "true" ]]; then
      continue
    fi

    # Remove the leading "+" marker.
    local dep_line="${line#+}"

    # Skip empty or whitespace-only lines.
    if [[ -z "${dep_line}" ]] || [[ "${dep_line}" =~ ^[[:space:]]*$ ]]; then
      continue
    fi

    # Skip comment lines.
    if [[ "${dep_line}" =~ ^[[:space:]]*# ]]; then
      continue
    fi

    # Pattern 1: Inline version string.
    #   crate_name = "1.0.0"
    if [[ "${dep_line}" =~ ^[[:space:]]*([a-zA-Z0-9_-]+)[[:space:]]*=[[:space:]]*\"([^\"]*)\" ]]; then
      local crate_name="${BASH_REMATCH[1]}"
      local new_version="${BASH_REMATCH[2]}"
      crates+=("${crate_name}|${new_version}")
      continue
    fi

    # Pattern 2: Table format with version key.
    #   crate_name = { version = "1.0.0", features = [...] }
    if [[ "${dep_line}" =~ ^[[:space:]]*([a-zA-Z0-9_-]+)[[:space:]]*=[[:space:]]*\{.*version[[:space:]]*=[[:space:]]*\"([^\"]*)\" ]]; then
      local crate_name="${BASH_REMATCH[1]}"
      local new_version="${BASH_REMATCH[2]}"
      crates+=("${crate_name}|${new_version}")
      continue
    fi

    # Pattern 3: Table format without a version (path, git, or workspace dependency).
    #   crate_name = { path = "../other" }
    #   crate_name = { git = "https://..." }
    #   crate_name.workspace = true
    if [[ "${dep_line}" =~ ^[[:space:]]*([a-zA-Z0-9_-]+)[[:space:]]*= ]]; then
      local crate_name="${BASH_REMATCH[1]}"
      crates+=("${crate_name}|")
      continue
    fi
  done <<< "${diff_output}"

  # Read the base version of this Cargo.toml for old version lookups.
  local base_cargo
  base_cargo="$(git show "${base_sha}:${cargo_file}" 2>/dev/null || true)"

  # For each changed crate, try to find the old version from the base SHA's
  # Cargo.toml to produce "crate@old..new" output.
  for entry in "${crates[@]}"; do
    local crate_name="${entry%%|*}"
    local new_version="${entry##*|}"

    local old_version=""
    if [[ -n "${base_cargo}" ]]; then
      # Try to find the old version of this crate in the base Cargo.toml.
      # Pattern for inline: crate_name = "version"
      local old_line
      old_line="$(echo "${base_cargo}" | grep -E "^[[:space:]]*${crate_name}[[:space:]]*=" 2>/dev/null | head -1 || true)"

      if [[ -n "${old_line}" ]]; then
        # Extract version from inline format: crate = "version"
        if [[ "${old_line}" =~ =[[:space:]]*\"([^\"]*)\" ]]; then
          old_version="${BASH_REMATCH[1]}"
        # Extract version from table format: crate = { version = "version", ... }
        elif [[ "${old_line}" =~ version[[:space:]]*=[[:space:]]*\"([^\"]*)\" ]]; then
          old_version="${BASH_REMATCH[1]}"
        fi
      fi
    fi

    # Format the output depending on whether we found version information.
    if [[ -n "${old_version}" && -n "${new_version}" && "${old_version}" != "${new_version}" ]]; then
      # Version was changed.
      echo "${crate_name}@${old_version}..${new_version}"
    elif [[ -n "${new_version}" ]]; then
      # New dependency or version unchanged.
      echo "${crate_name}@${new_version}"
    else
      # Fallback: just the crate name (e.g., path/git/workspace dependencies).
      echo "${crate_name}"
    fi
  done
}
