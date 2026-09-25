#!/bin/bash
# Writes the single-use marker file git-kit's PreToolUse hard-block hooks
# (hooks/scripts/git-guard-raw-commit.sh, hooks/scripts/git-guard-raw-pr-ops.sh,
# hooks/scripts/git-guard-raw-branch-create.sh, hooks/scripts/git-guard-raw-pr-review.sh,
# hooks/scripts/git-guard-raw-destructive-cleanup.sh)
# check before allowing a raw `git commit` / `gh pr create` / `gh pr merge` /
# `git checkout -b` / `git switch -c` / `gh pr review` / `gh pr comment` /
# `gh api .../pulls/*/comments/*/replies` / any `gh api graphql` call /
# `git branch -D <protected-branch>` / `git worktree remove` through.
#
# Called by the allowlisted skills (commit, standalone-commits, create-pr,
# merge-pr, starting-work, collaborating-on-a-pr, explain-pr-changes, git-cleanup,
# codex-review-recovery, handling-review-findings)
# immediately before they run the guarded command themselves --
# the marker must be fresh (<=60s old, checked by the hook) and is consumed
# on first use, so writing it any earlier than "right before the guarded
# command" risks it going stale or being consumed by an unrelated call.
#
# WARNING (issue #165): this script only writes the marker -- it does not, and
# cannot, verify that the calling skill's own documented procedure (staging
# review, sensitive-file scan, round/dedup budgeting, etc.) actually ran.
# Invoking this script by hand, outside a real Skill() dispatch of one of the
# skills listed above, produces a marker indistinguishable from a genuine one
# and lets the raw guarded command through with none of that skill's own
# safeguards applied. Never invoke this script directly as a shortcut past a
# skill's own procedure -- always dispatch the skill itself and let it call
# this script as its own last step.
set -euo pipefail

GUARD_TYPE="${1:?usage: git-write-marker.sh <guard-type> <skill-name>}"
SKILL_NAME="${2:?usage: git-write-marker.sh <guard-type> <skill-name>}"

case "$GUARD_TYPE" in
  git-commit|gh-pr-create|gh-pr-merge|git-branch-create|gh-pr-review|git-cleanup-destructive) ;;
  *)
    echo "Error: unknown guard type '$GUARD_TYPE' (expected git-commit, gh-pr-create, gh-pr-merge, git-branch-create, gh-pr-review, or git-cleanup-destructive)" >&2
    exit 1
    ;;
esac

GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || { echo "Error: not inside a git repository" >&2; exit 1; }
MARKER="$GIT_DIR/git-kit-marker.txt"

# Write atomically: a plain truncating redirect lets a concurrent guard-script
# read observe a momentarily empty or partially-written file, since Claude
# Code can dispatch independent tool calls in parallel within one turn.
# Writing to a unique temp file in the same directory then renaming into
# place means any reader sees either the complete old marker or the complete
# new one, never a partial write -- rename is atomic on the same filesystem.
TMP="$MARKER.tmp.$$"
echo "$GUARD_TYPE $(date +%s) $SKILL_NAME" > "$TMP"
mv -f "$TMP" "$MARKER"
