#!/bin/bash
# Stop guard: blocks the agent's turn from ending while the current worktree
# is one `starting-work` locked to this session (per its own lock step) and
# that worktree has uncommitted changes or commits neither in the resolved
# default branch nor pushed to the branch's origin upstream. Exists because Claude Code's built-in worktree exit flow
# (EnterWorktree/ExitWorktree) can remove a session's bound worktree on exit
# -- this hook makes sure nothing gets silently lost in that moment.
#
# Escape hatch: if the most recent user message, trimmed, is exactly
# "exit anyway" (case-insensitive) -- not merely containing that phrase --
# the block is skipped for this turn. Whole-message match deliberately, so
# untrusted text quoted elsewhere in the transcript (a PR body, a tool
# result) can't accidentally or deliberately trigger the override.
set -euo pipefail
START=$SECONDS # the history-check budget below counts from here, not from its first use

INPUT=$(cat)

# Fail closed, not open: if jq isn't available, every call below would crash
# under set -e -- which, under this hook's "onError": "warn" registration,
# lets the turn end with just a warning, silently disabling the exact
# dirty-worktree-loss protection this hook exists to provide. Emit an
# explicit block instead, so a missing dependency can't silently defeat it --
# same fail-closed pattern the 5 PreToolUse guard scripts already use.
#
# Loop-safety without jq: a hard block here must still honor stop_hook_active
# the same way the jq-based check below does, or a session with no jq at all
# would block forever with no way to ever finish a turn. Check the raw JSON
# text for the field with grep instead -- crude, but doesn't need jq to avoid
# an infinite loop.
if ! command -v jq >/dev/null 2>&1; then
  if echo "$INPUT" | grep -qE '"stop_hook_active"[[:space:]]*:[[:space:]]*true'; then
    exit 0 # already continuing from a previous block -- avoid an infinite loop
  fi
  cat <<'EOF'
{
  "decision": "block",
  "reason": "git-kit's dirty-worktree-exit guard requires `jq`, which isn't available in this environment -- install jq so this guard can verify whether the session's bound worktree has unprotected work before the turn ends. Say \"exit anyway\" and try again to override once, if you're sure nothing needs protecting.",
  "systemMessage": "Dirty-worktree-exit guard requires jq -- install it to restore this protection, or say \"exit anyway\" to override once."
}
EOF
  exit 0
fi

STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
  exit 0 # already continuing from a previous block -- avoid an infinite loop
fi

git rev-parse --git-dir >/dev/null 2>&1 || exit 0 # not in a git repo
TOPLEVEL=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0

# Only enforce for a worktree starting-work actually locked to a session --
# never for the main checkout or a worktree created some other way.
WORKTREE_INFO=$(git worktree list --porcelain 2>/dev/null || true)
LOCK_REASON=$(printf '%s\n' "$WORKTREE_INFO" | awk -v top="$TOPLEVEL" '
  /^worktree / { path=substr($0, 10); in_block=(path==top) }
  in_block && /^locked/ { sub(/^locked ?/, ""); print; exit }
')
if [ -z "$LOCK_REASON" ] || ! printf '%s' "$LOCK_REASON" | grep -qi "claude session"; then
  exit 0
fi

DIRTY=false
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  DIRTY=true
fi

UNMERGED=false
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@') || true
DEFAULT_BRANCH="${DEFAULT_BRANCH:-main}"
# Compare by patch content, not SHA reachability: a rebase- or squash-merge
# lands the branch's commits on the default branch under new SHAs, so a
# `git log origin/<default>..HEAD` range reports already-merged work as
# unmerged (issue #707). `git cherry` marks a commit `-` when an equivalent
# patch is already upstream and `+` when it isn't. A missing upstream ref
# keeps the earlier behavior (no unmerged state reported); a cherry failure
# or timeout with the ref present fails toward warning. `git cherry` skips
# merge commits, so a merge commit in the range keeps the warning too (it can
# carry the only unlanded change, e.g. a conflict resolution). Patch-id
# equivalence ignores whitespace, and a commit landed then reverted upstream
# still counts as landed: both accepted limitations.
#
# Every history check below runs under one shared budget of 5s counted from
# script start, minus 1s per call for whole-second rounding and the last
# call's kill grace, and the transcript parse further down has its own 2s
# cap: together they leave headroom under the 10s registration limit, since
# a hook timeout under onError "warn" would end the turn with only a warning.
# This makes an overrun unlikely, not impossible: the unbounded `git status`
# above and process start-up still count against the limit. A check that runs
# out of budget or fails keeps the warning. Without `timeout` nothing can be
# bounded, so only a single-commit range probe runs (the behavior before
# issue #707: a rebase- or squash-merged branch warns; the probe still walks
# the range, like the earlier `git log` did) and the pushed and merged-PR
# checks are skipped.
HAS_TIMEOUT=false
command -v timeout >/dev/null 2>&1 && HAS_TIMEOUT=true
BUDGET_END=$((START + 5))
bounded() { # bounded <max-seconds> <command...>: exit 124 once the budget is spent
  local cap="$1" left=$((BUDGET_END - SECONDS - 1))
  shift
  [ "$left" -lt "$cap" ] && cap="$left"
  [ "$cap" -ge 1 ] || return 124
  timeout -k 1 "$cap" "$@"
}
if git rev-parse --verify --quiet "origin/$DEFAULT_BRANCH^{commit}" >/dev/null 2>&1; then
  if [ "$HAS_TIMEOUT" = true ]; then
    CHERRY=$(bounded 3 git cherry "origin/$DEFAULT_BRANCH" HEAD 2>/dev/null) || CHERRY="+ cherry-failed"
    MERGES=$(bounded 2 git rev-list --merges "origin/$DEFAULT_BRANCH..HEAD" 2>/dev/null) || MERGES="merges-failed"
  else
    CHERRY=""
    MERGES=$(git rev-list --max-count=1 "origin/$DEFAULT_BRANCH..HEAD" 2>/dev/null) || MERGES="range-failed"
  fi
  if grep -q '^+' <<<"$CHERRY" || [ -n "$MERGES" ]; then
    UNMERGED=true
  fi
fi

# Commits already pushed to the branch's origin upstream are safe: removing
# the worktree cannot lose them. Only an upstream under refs/remotes/origin/
# counts, the same repository the merged-PR check below is bound to, and the
# branch's configured remote must itself be origin: a fork whose refspec maps
# into refs/remotes/origin/, or a remote named origin/<x>, still resolves
# there. A local branch or another remote as upstream keeps the warning. This
# is a convenience check against accidental loss, not proof of a push: the
# remote-tracking ref is a local ref, read from the last fetch or push (a
# remote branch deleted since then still reads as pushed) and writable
# locally. Accepted: removal keeps the local branch, and a merge-time deletion
# is covered above.
if [ "$UNMERGED" = true ] && [ "$HAS_TIMEOUT" = true ]; then
  BRANCH=$(git symbolic-ref --quiet --short HEAD 2>/dev/null) || BRANCH=""
  BRANCH_REMOTE=""
  [ -n "$BRANCH" ] && { BRANCH_REMOTE=$(git config --get "branch.$BRANCH.remote" 2>/dev/null) || BRANCH_REMOTE=""; }
  UPSTREAM_REF=$(git rev-parse --symbolic-full-name '@{upstream}' 2>/dev/null) || UPSTREAM_REF=""
  if [ "$BRANCH_REMOTE" = origin ] && [[ "$UPSTREAM_REF" == refs/remotes/origin/?* ]]; then
    bounded 1 git merge-base --is-ancestor HEAD "$UPSTREAM_REF" 2>/dev/null && UNMERGED=false
  fi
fi

# A squash-merge of several commits matches no single branch commit's patch,
# so `git cherry` still reports `+`. Fall back to the branch's PR: treat the
# work as merged only when the PR is MERGED into $DEFAULT_BRANCH of origin's
# own repository and its head SHA is exactly this worktree's HEAD (nothing
# committed after the merged head). Needs `gh`, `timeout` and network access;
# any failure, timeout or mismatch keeps the warning. The PR is looked up by
# the current branch's name with --repo set to origin's owner/name (gh needs
# an explicit branch once --repo is given), so neither GH_REPO (also
# dropped), a `gh repo set-default` nor an `upstream` remote can pick another
# repository; the PR's repository is still compared against origin's. An
# origin that isn't on github.com, or a detached HEAD, skips the lookup and
# the warning stays. The gh output is only compared as a string, never run.
# A PR merged and later reverted on the default branch still counts as merged
# (accepted: the work stays in GitHub's PR history).
if [ "$UNMERGED" = true ] && [ "$HAS_TIMEOUT" = true ] && command -v gh >/dev/null 2>&1; then
  HEAD_SHA=$(git rev-parse HEAD 2>/dev/null) || HEAD_SHA=""
  PR_BRANCH=$(git symbolic-ref --quiet --short HEAD 2>/dev/null) || PR_BRANCH=""
  ORIGIN_REPO=$(git remote get-url origin 2>/dev/null | sed -E 's#^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)##; s#\.git$##; s#/$##') || ORIGIN_REPO=""
  [[ "$ORIGIN_REPO" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]] || ORIGIN_REPO=""
  PR_STATE=""
  if [ -n "$HEAD_SHA" ] && [ -n "$PR_BRANCH" ] && [ -n "$ORIGIN_REPO" ]; then
    # `--` keeps a branch name starting with `-` (possible via update-ref) from parsing as a gh option.
    PR_STATE=$(bounded 3 env -u GH_REPO gh pr view --repo "$ORIGIN_REPO" --json state,baseRefName,headRefOid,url \
      --jq '.state + " " + .baseRefName + " " + .headRefOid + " " + (.url | sub("^https://github\\.com/"; "") | sub("/pull/[0-9]+$"; ""))' \
      -- "$PR_BRANCH" 2>/dev/null) || PR_STATE=""
  fi
  if [ -n "$PR_STATE" ] && [ "$PR_STATE" = "MERGED $DEFAULT_BRANCH $HEAD_SHA $ORIGIN_REPO" ]; then
    UNMERGED=false
  fi
fi

if [ "$DIRTY" = false ] && [ "$UNMERGED" = false ]; then
  exit 0 # clean -- nothing to protect
fi

TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // empty')
if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ]; then
  # Trimmed to a whole-message match, not a substring search -- a real override
  # is a short, deliberate command, never text embedded inside a longer PR
  # body, tool result, or system-reminder block quoted in the transcript.
  # Bounded to the transcript's tail: the override, if present, is always the
  # most recent user turn, and Stop must stay quick -- an unbounded jq -rs
  # over a long session's full JSONL both wastes time and risks a timeout,
  # which (per Stop's own timeout semantics) fails this guard open. The parse
  # gets its own 2s cap rather than the history budget, so a slow repository
  # can never make the "exit anyway" override unusable; a timeout leaves the
  # message empty, which keeps the block.
  PARSE_LIMIT=()
  [ "$HAS_TIMEOUT" = true ] && PARSE_LIMIT=(timeout -k 1 2)
  LAST_USER_MSG=$(tail -n 200 "$TRANSCRIPT_PATH" 2>/dev/null | ${PARSE_LIMIT[@]+"${PARSE_LIMIT[@]}"} jq -rs '
    [.[] | select(.type == "user" and (.message.role // empty) == "user")]
    | if length == 0 then "" else
        last | .message.content
        | if type == "string" then . else
            map(select(.type == "text") | .text) | join(" ")
          end
      end
    | gsub("^\\s+|\\s+$"; "")
  ' 2>/dev/null) || LAST_USER_MSG="" # a killed parse drops its partial output
  LAST_USER_MSG_LOWER=$(printf '%s' "$LAST_USER_MSG" | tr '[:upper:]' '[:lower:]')
  if [ "$LAST_USER_MSG_LOWER" = "exit anyway" ]; then
    exit 0
  fi
fi

STATE_DESC="uncommitted changes"
if [ "$DIRTY" = true ] && [ "$UNMERGED" = true ]; then
  STATE_DESC="uncommitted changes and commits not yet in $DEFAULT_BRANCH"
elif [ "$UNMERGED" = true ]; then
  STATE_DESC="commits not yet in $DEFAULT_BRANCH"
fi

jq -n \
  --arg path "$TOPLEVEL" \
  --arg state "$STATE_DESC" \
  '{
    "decision": "block",
    "reason": ("This session'\''s bound worktree at " + $path + " has " + $state + ". Tell the user plainly: exiting now could lose this work if the worktree gets removed. Suggest committing (Skill(commit)) or pushing first. If they want to exit anyway, they can say \"exit anyway\" and try again."),
    "systemMessage": ("Bound worktree has " + $state + " -- say \"exit anyway\" to override.")
  }'
exit 0
