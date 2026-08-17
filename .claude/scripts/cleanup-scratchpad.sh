#!/usr/bin/env bash
# Manually delete old session-scratchpad directories for this project
# (%LOCALAPPDATA%\Temp\claude\<sanitized-repo-path>\<session-uuid>\).
# rm -rf is blocked when Claude runs it, so this is meant to be run by hand,
# from your own terminal (Git Bash), not from inside a Claude Code session.
set -euo pipefail

DAYS="${1:-7}"

if ! [[ "$DAYS" =~ ^[0-9]+$ ]]; then
  echo "Usage: $0 [days-threshold]" >&2
  echo "  days-threshold must be a non-negative integer (default: 7)" >&2
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Not inside a git repository." >&2
  exit 1
}

WIN_PATH="$(cygpath -w "$REPO_ROOT")"
SANITIZED="$(printf '%s' "$WIN_PATH" | tr ':\\' '--')"

TARGET="$(cygpath -u "$LOCALAPPDATA")/Temp/claude/$SANITIZED"

if [[ ! -d "$TARGET" ]]; then
  echo "No scratchpad directory found at: $TARGET"
  exit 0
fi

echo "Scanning $TARGET for session directories older than $DAYS day(s)..."
echo

NOW=$(date +%s)
THRESHOLD_SECONDS=$((DAYS * 86400))
TO_DELETE=()
TOTAL_KB=0

while IFS= read -r -d '' dir; do
  newest="$(find "$dir" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1)"
  if [[ -z "$newest" ]]; then
    newest="$(stat -c '%Y' "$dir")"
  else
    newest="${newest%.*}"
  fi
  age=$((NOW - newest))
  if (( age >= THRESHOLD_SECONDS )); then
    size_kb="$(du -sk "$dir" | cut -f1)"
    size_human="$(du -sh "$dir" | cut -f1)"
    age_days=$((age / 86400))
    echo "  $(basename "$dir")  (${age_days}d old, ${size_human})"
    TO_DELETE+=("$dir")
    TOTAL_KB=$((TOTAL_KB + size_kb))
  fi
done < <(find "$TARGET" -mindepth 1 -maxdepth 1 -type d -print0)

if [[ ${#TO_DELETE[@]} -eq 0 ]]; then
  echo "Nothing older than $DAYS day(s) to delete."
  exit 0
fi

PLURAL="ies"
[[ ${#TO_DELETE[@]} -eq 1 ]] && PLURAL="y"

echo
echo "${#TO_DELETE[@]} director${PLURAL} found, totaling $((TOTAL_KB / 1024)) MB."
read -r -p "Delete these directories? [y/N] " ANSWER

case "$ANSWER" in
  [yY]|[yY][eE][sS])
    for dir in "${TO_DELETE[@]}"; do
      rm -rf "$dir"
      echo "Deleted: $dir"
    done
    echo "Done."
    ;;
  *)
    echo "Cancelled — nothing deleted."
    ;;
esac
