#!/bin/bash
# PreToolUse guard: hard-blocks a raw `git branch -D <protected-branch>` or
# a raw `git worktree remove --force` invocation that wasn't immediately
# preceded by git-cleanup's own marker handshake. Same mechanism as
# guard-raw-branch-create.sh (see that script's header comment for the full
# marker-handshake rationale).
#
# Scoped narrower than a blanket `-D` guard: `git branch -D <name>` is only
# guarded when <name> matches one of git-cleanup's own protected-branch
# patterns (main, master, develop, release/*) -- git-cleanup's normal
# workflow force-deletes plenty of non-protected branches (its SQUASH_MERGED/
# SUPERSEDED categories) and shouldn't need a marker write for every one of
# those, the same way guard-raw-branch-create.sh deliberately leaves bare
# `git branch <name>` unguarded to avoid blocking routine, harmless calls.
# `git worktree remove` is scoped to only the `--force`/`-f` form -- a plain
# `git worktree remove` already refuses on a dirty or locked worktree via
# git's own built-in safeguard, so it isn't the irreversible case this guard
# exists to catch. Scoping to the forced form also avoids blocking other
# skills (e.g. git-worktrees' own documented cleanup steps) that call plain
# `git worktree remove` without git-cleanup's marker handshake.
set -euo pipefail

# Fail closed, not open: if jq isn't available, the script below can't parse
# INPUT and would otherwise crash -- which, under this hook's "onError": "warn"
# registration, lets the tool call proceed with just a warning. Emit an
# explicit deny instead, so a missing dependency can't silently defeat this
# guard.
if ! command -v jq >/dev/null 2>&1; then
  cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "git-kit's destructive-cleanup guard requires `jq`, which isn't available in this environment -- install jq or this guard cannot verify the command is safe."
  }
}
EOF
  exit 0
fi

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if { [ "$TOOL_NAME" != "Bash" ] && [ "$TOOL_NAME" != "PowerShell" ]; } || [ -z "$COMMAND" ]; then
  exit 0
fi

# git(\.exe)? also catches the literal `git.exe` invocation PowerShell callers
# sometimes use. The repeating group catches zero or more interposed global
# options -- `-C <dir>`/`-c <k>=<v>` (each a separate space-delimited value
# token) or any other single-token `-`/`--` flag -- same prefix pattern
# guard-raw-commit.sh and guard-raw-branch-create.sh already use.
GIT_PREFIX='(^|[;&|]|[[:space:]])git(\.exe)?([[:space:]]+(-[Cc][[:space:]]+[^[:space:]]+|--?[^[:space:]]+))*[[:space:]]+'

# Consume our own marker on every Bash/PowerShell call, before the MATCH
# check below -- not just on the call that turns out to match. Consuming
# only inside the MATCH branch (the original ordering) let a
# "git-cleanup-destructive" marker survive its full 60s TTL untouched
# through any number of intervening non-matching commands, so a later,
# unrelated destructive command within that window could still be
# authorized by a marker meant for an earlier, different command. Reading
# and consuming here instead shrinks the marker's live window to "the very
# next Bash/PowerShell call after it was written", matching the single-use
# intent the write side already documents. Only a marker whose `guard`
# field is this guard's own type is touched -- a marker written for a
# sibling guard (`commit`'s, `create-pr`'s, etc.) is left alone so this
# guard never consumes another guard's single-use token.
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || exit 0 # not in a git repo -- nothing to guard
MARKER="$GIT_DIR/git-kit-marker.txt"

now=$(date +%s)
allowed=false

if [ -f "$MARKER" ]; then
  read -r guard ts _skill < "$MARKER" || true
  guard="${guard:-}"  # defensive: a concurrent/partial read under `set -u` must degrade to "no marker", never crash
  if [ "$guard" = "git-cleanup-destructive" ]; then
    case "${ts:-}" in '' | *[!0-9]*) ts="" ;; esac  # digits-only -- never reaches arithmetic otherwise
    if [ -n "$ts" ] && [ $((now - ts)) -le 60 ]; then
      allowed=true
    fi
    rm -f "$MARKER" # consume as soon as seen -- single use, regardless of whether this call turns out to MATCH below
  fi
fi

MATCH=false

# `git branch -D <name>` (or the equivalent `-d -f`/`-f -d`/`-df`/`-fd`/
# `--delete --force` spellings) -- only when <name> is one of the protected
# patterns. <name> may optionally be quoted -- `git-cleanup/SKILL.md` itself
# instructs quoting the branch variable, so an unquoted-only match would miss
# the exact form that skill is told to write.
DELETE_FLAG='(-D|--delete[[:space:]]+--force|--force[[:space:]]+--delete|-d[[:space:]]+-f|-f[[:space:]]+-d|-df|-fd)'
if echo "$COMMAND" | grep -qE "${GIT_PREFIX}branch([[:space:]]+-[^[:space:]]+)*[[:space:]]+${DELETE_FLAG}([[:space:]]+-[^[:space:]]+)*[[:space:]]+[\"']?(main|master|develop|release/[^[:space:]\"']*)[\"']?([[:space:]]|\$)"; then
  MATCH=true
fi

# `git worktree remove --force`/`-f` only -- plain `remove` (no force flag)
# already refuses on a dirty or locked worktree via git's own safeguard.
# `--force`/`-f` can legally appear either before or after the worktree path
# argument (`git worktree remove --force <path>` and
# `git worktree remove <path> --force` are both valid git syntax), so a
# single regex requiring the flag to immediately follow `remove` (with only
# `-`-prefixed tokens permitted in between) misses the path-before-flag form
# entirely -- live-verified: that form produced no denial at all.
#
# The force-flag check is scoped to each `worktree remove` invocation's own
# argument span (from `remove` up to the next `;`/`&`/`|` command separator
# or end of string), not run independently against the whole `$COMMAND`
# string -- `$COMMAND` is the raw Bash/PowerShell tool_input.command and can
# legally contain multiple chained sub-commands (`&&`/`;`/`|`). An earlier
# version of this check ran `WORKTREE_REMOVE_RE`/`FORCE_FLAG_RE` as two fully
# independent conditions against the entire string, which meant a bare `-f`
# anywhere in the whole command -- e.g. an unrelated chained
# `rm -f`/`make -f`/`docker ... -f` -- would falsely deny a `git worktree
# remove <path>` call that itself had no force flag at all (live-verified:
# `git worktree remove ./clean-path && rm -f tmpfile` was denied even though
# the worktree-remove half had no force flag). Bounding the force-flag check
# to just the matched invocation's own span (excluding `;`/`&`/`|`) closes
# that false-positive while still catching a force flag anywhere within a
# genuine `worktree remove` call's own argument list.
FORCE_FLAG_RE='(^|[[:space:]])(--force|-f)([[:space:]]|$)'
WORKTREE_REMOVE_SPANS=$(echo "$COMMAND" | grep -oE "${GIT_PREFIX}worktree[[:space:]]+remove[^;&|]*" || true)
if [ -n "$WORKTREE_REMOVE_SPANS" ] && echo "$WORKTREE_REMOVE_SPANS" | grep -qE "$FORCE_FLAG_RE"; then
  MATCH=true
fi

if [ "$MATCH" != true ]; then
  exit 0
fi

if [ "$allowed" = true ]; then
  exit 0
fi

cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Raw `git branch -D` targeting a protected branch (main/master/develop/release/*), or raw `git worktree remove --force`, is blocked by git-kit's destructive-cleanup guard. Use the `git-cleanup` skill (`/git-cleanup`) instead -- it gates these irreversible actions behind explicit user confirmation. If this fired from inside git-cleanup itself, its marker-write step is missing or ran too late -- the marker must be written immediately before this command."
  }
}
EOF
exit 0
