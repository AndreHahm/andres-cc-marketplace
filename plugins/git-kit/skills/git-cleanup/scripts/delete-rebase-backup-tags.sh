#!/usr/bin/env bash
# Lists (--list) or deletes (by index) leftover git-rebase-sync rebase-backup
# tags git-cleanup's Phase 3.6 has verified safe to delete. A tag name is
# untrusted content -- git's own ref-name rules permit almost every shell
# metacharacter (`$(cmd)`, backticks, `;`, `&`, `|`, etc. are all legal in a
# tag name; live-verified), so no character-class check on a value the agent
# then types into a command is ever fully safe, and no such check can also
# stay complete against every legal name. This script never receives a tag
# name as an argument or on stdin: `--list` re-derives the deletable-tag list
# itself and persists it to a snapshot file (NUL-delimited, raw bytes); the
# delete mode reads that exact snapshot back rather than recomputing it --
# closing a race where repo state changes between the two calls could
# otherwise resolve the same index to a different tag the second time,
# mirroring stage-selected-files.sh's own snapshot rationale. The model only
# ever has to pass back plain digit indices, never a single character of
# untrusted tag-name content.
#
# Called by the git-cleanup skill's Phase 5: run `--list` first (this is also
# safe to run standalone for Gate 1's own candidate list), present the
# numbered output to the user, then re-invoke with the chosen indices once
# the user confirms at Gate 2.
set -euo pipefail

git rev-parse --git-dir >/dev/null 2>&1 || { echo "Error: not inside a git repository" >&2; exit 1; }
cd "$(git rev-parse --show-toplevel)"

SNAPSHOT="$(git rev-parse --git-dir)/delete-rebase-backup-tags.snapshot"

# Get default branch name. Not `... || echo "main"` -- `sed` exits 0 even on
# empty stdin (no origin/HEAD symref set), so the `||` fallback never fires
# and default_branch would silently resolve to an empty string. Same fix as
# phase1-analysis.sh's own default-branch resolution (PR #262 review).
default_branch=$(git symbolic-ref refs/remotes/origin/HEAD \
  2>/dev/null | sed 's@^refs/remotes/origin/@@')
default_branch="${default_branch:-main}"

# Independently re-derives which rebase-backup tags are safe to delete --
# same rule Phase 3.6 documents (branch gone or merged AND the tag's own
# commit reachable from the default branch), recomputed fresh here rather
# than trusting an earlier read, per
# .claude/rules/recheck-state-before-side-effecting-action.md.
list_deletable() {
  for tag in $(git tag -l '*-rebase-backup-*'); do
    if [[ "$tag" =~ ^(.+)-rebase-backup-[0-9]{8}-[0-9]{6}$ ]]; then
      branch="${BASH_REMATCH[1]}"
      branch_gone=false
      branch_merged=false
      if git show-ref --verify --quiet "refs/heads/$branch"; then
        if git branch --merged "$default_branch" --format='%(refname:short)' \
          | grep -qxF "$branch"; then
          branch_merged=true
        fi
      else
        branch_gone=true
      fi
      if $branch_gone || $branch_merged; then
        if git merge-base --is-ancestor "$tag" "$default_branch" 2>/dev/null; then
          printf '%s\0' "$tag"
        fi
      fi
    fi
  done
}

if [ "${1:-}" = "--list" ]; then
  list_deletable > "$SNAPSHOT"
  i=0
  while IFS= read -r -d '' tag; do
    i=$((i + 1))
    # %q (display only): a tag name can contain characters that would make
    # the numbered listing itself misleading -- the snapshot file and the
    # `git tag -d` argument below both keep the raw, unescaped bytes; only
    # this printed line is quoted for safe, unambiguous display.
    printf '%d\t%q\n' "$i" "$tag"
  done < "$SNAPSHOT"
  exit 0
fi

if [ "$#" -eq 0 ]; then
  echo "Usage: $0 --list | <index> [index...]" >&2
  exit 2
fi

if [ ! -f "$SNAPSHOT" ]; then
  echo "Error: no candidate list found -- run --list first" >&2
  exit 2
fi

declare -A wanted
for arg in "$@"; do
  if ! [[ "$arg" =~ ^[0-9]+$ ]]; then
    echo "Error: index '$arg' is not a positive integer" >&2
    exit 2
  fi
  wanted["$arg"]=1
done

matched=()
i=0
while IFS= read -r -d '' tag; do
  i=$((i + 1))
  if [ -n "${wanted[$i]:-}" ]; then
    matched+=("$tag")
  fi
done < "$SNAPSHOT"

if [ "${#matched[@]}" -ne "${#wanted[@]}" ]; then
  echo "Error: one or more requested indices are out of range -- run --list again and retry" >&2
  exit 1
fi

# Each deletion is a separate `git tag -d` call so one failure doesn't block
# the rest -- same partial-failure principle Phase 5 already documents for
# branch deletions. `$tag` here is a shell variable holding raw bytes read
# from the snapshot file, never text the model composed into this command.
failed=0
for tag in "${matched[@]}"; do
  if git tag -d -- "$tag"; then
    :
  else
    echo "Error: failed to delete tag '$tag'" >&2
    failed=1
  fi
done

rm -f "$SNAPSHOT"
exit "$failed"
