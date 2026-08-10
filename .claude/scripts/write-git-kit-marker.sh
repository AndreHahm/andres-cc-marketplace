#!/bin/bash
# Writes the single-use marker file git-kit's PreToolUse hard-block hooks
# (hooks/scripts/guard-raw-commit.sh, hooks/scripts/guard-raw-pr-ops.sh,
# hooks/scripts/guard-raw-branch-create.sh, hooks/scripts/guard-raw-pr-review.sh)
# check before allowing a raw `git commit` / `gh pr create` / `gh pr merge` /
# `git checkout -b` / `git switch -c` / `gh pr review` / `gh pr comment` through.
#
# Called by the allowlisted skills (commit, standalone-commits, create-pr,
# merge-pr, starting-work, collaborating-on-a-pr) immediately before they run
# the guarded command themselves --
# the marker must be fresh (<=60s old, checked by the hook) and is consumed
# on first use, so writing it any earlier than "right before the guarded
# command" risks it going stale or being consumed by an unrelated call.
set -euo pipefail

GUARD_TYPE="${1:?usage: write-git-kit-marker.sh <guard-type> <skill-name>}"
SKILL_NAME="${2:?usage: write-git-kit-marker.sh <guard-type> <skill-name>}"

case "$GUARD_TYPE" in
  git-commit|gh-pr-create|gh-pr-merge|git-branch-create|gh-pr-review) ;;
  *)
    echo "Error: unknown guard type '$GUARD_TYPE' (expected git-commit, gh-pr-create, gh-pr-merge, git-branch-create, or gh-pr-review)" >&2
    exit 1
    ;;
esac

GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || { echo "Error: not inside a git repository" >&2; exit 1; }
echo "$GUARD_TYPE $(date +%s) $SKILL_NAME" > "$GIT_DIR/git-kit-marker.txt"
