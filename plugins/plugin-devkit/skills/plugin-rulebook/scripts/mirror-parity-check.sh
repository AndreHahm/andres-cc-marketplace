#!/bin/bash
# R19 Mirror Parity Check: find drift between a plugin's .claude/ staging
# mirror and its plugins/<name>/ canonical source, for skills, agents,
# commands, rules, hooks/scripts, and (for scripts_mirrors plugins) scripts. Only compares
# component/file pairs present in BOTH trees -- a name that exists in only
# one tree belongs to a different plugin's own .claude/ mirror (e.g.
# git-kit's skills sitting alongside plugin-devkit's in the shared .claude/
# directory) and is not a drift finding.
#
# Usage: mirror-parity-check.sh <plugin-name>
# Example: mirror-parity-check.sh plugin-devkit
#
# Exit 0: no drift found. Exit 1: drift found (for pre-commit/CI use).

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <plugin-name>" >&2
  echo "Example: $0 plugin-devkit" >&2
  exit 1
fi

PLUGIN="$1"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
CANONICAL="$REPO_ROOT/plugins/$PLUGIN"
MIRROR="$REPO_ROOT/.claude"

if [ ! -d "$CANONICAL" ]; then
  echo "No such plugin directory: $CANONICAL" >&2
  exit 1
fi

DRIFT_FOUND=0

check_component_type() {
  local subdir="$1"
  local canonical_dir="$CANONICAL/$subdir"
  [ -d "$canonical_dir" ] || return 0

  for entry in "$canonical_dir"/*; do
    [ -e "$entry" ] || continue
    local name
    name="$(basename "$entry")"
    local mirror_entry="$MIRROR/$subdir/$name"

    if [ ! -e "$mirror_entry" ]; then
      echo "MISSING IN MIRROR: $subdir/$name (exists in plugins/$PLUGIN, absent from .claude/)"
      DRIFT_FOUND=1
      continue
    fi

    if [ -d "$entry" ]; then
      if ! diff -rq "$mirror_entry" "$entry" > /dev/null 2>&1; then
        echo "DRIFT: $subdir/$name"
        DRIFT_FOUND=1
      fi
    else
      if ! diff -q "$mirror_entry" "$entry" > /dev/null 2>&1; then
        echo "DRIFT: $subdir/$name"
        DRIFT_FOUND=1
      fi
    fi
  done
}

check_component_type "skills"
check_component_type "agents"
check_component_type "commands"
check_component_type "rules"
check_component_type "hooks/scripts"

# scripts/ is mirrored flat into .claude/scripts/ only for the plugins listed
# in .claude/marketplace-sync.json's scripts_mirrors; for any other plugin a
# canonical scripts/ file is not expected in the mirror, so it is not checked.
# Skipped (not failed) when the sync file or python3 is unavailable.
if python3 -c 'import json,sys; sys.exit(0 if sys.argv[2] in json.load(open(sys.argv[1])).get("scripts_mirrors", []) else 1)' \
  "$REPO_ROOT/.claude/marketplace-sync.json" "$PLUGIN" 2>/dev/null; then
  check_component_type "scripts"
fi

if [ "$DRIFT_FOUND" -eq 0 ]; then
  echo "No mirror drift found between .claude/ and plugins/$PLUGIN/."
fi

exit "$DRIFT_FOUND"
