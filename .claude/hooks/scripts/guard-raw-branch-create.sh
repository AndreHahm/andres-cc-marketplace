#!/bin/bash
# PreToolUse guard: hard-blocks a raw branch-creating command (`git checkout
# -b`/`-B`, `git switch -c`/`-C`/`--create`, `git worktree add -b`/`-B`,
# including one or more interposed global options -- `-C <dir>`/`-c <k>=<v>`
# in either case, or any other single-token `-`/`--` flag) that wasn't
# immediately preceded by starting-work's marker handshake. Same mechanism as
# guard-raw-commit.sh (see that script's header comment for the full
# marker-handshake rationale).
#
# Deliberately narrow: bare `git branch <name>` is NOT guarded here -- it's
# indistinguishable by regex alone from `git branch --show-current`/`-vv`/
# `--list`/etc., which starting-work, finishing-work, and commit all call
# read-only. A guard that can't tell those apart would block routine,
# harmless calls.
set -euo pipefail

# Fail closed on an unexpected non-zero exit below (not the deliberate deny
# paths, and not a context set -e already exempts -- an if/while/&&/||/case
# test). Residual, not covered by this trap: a fatal expansion error (an
# unbound variable, a bad arithmetic expression) is a parse-time error bash
# treats differently from a command's exit status, and a missing/
# non-executable interpreter or a hook timeout kill are outside this script's
# control entirely -- all three still fail open under this hook's "onError":
# "warn" registration. What this trap does close: an ordinary command
# failure (e.g. `jq` choking on malformed input) that would otherwise crash
# the script and let the guarded command through with no marker check at
# all. See issue #83.
fail_closed_deny() {
  cat <<'EOF' || true
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "git-kit's branch-creation guard failed unexpectedly and could not verify the command is safe -- denying by default rather than allowing it through unguarded."
  }
}
EOF
  exit 0
}
trap fail_closed_deny ERR

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
    "permissionDecisionReason": "git-kit's branch-creation guard requires `jq`, which isn't available in this environment -- install jq or this guard cannot verify the command is safe."
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

# Consume our own marker on every Bash/PowerShell call, before the command
# regex match below -- not just on the call that turns out to match. See
# guard-raw-destructive-cleanup.sh's header comment for the full rationale
# (consuming only inside the match branch let a marker survive its full 60s
# TTL through any number of intervening non-matching commands). Only a marker
# whose `guard` field is this guard's own type ("git-branch-create") is
# touched -- a marker written for a sibling guard is left alone.
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || exit 0 # not in a git repo -- nothing to guard
MARKER="$GIT_DIR/git-kit-marker.txt"

now=$(date +%s)
allowed=false

if [ -f "$MARKER" ]; then
  read -r guard ts _skill < "$MARKER" || true
  guard="${guard:-}"  # defensive: a concurrent/partial read under `set -u` must degrade to "no marker", never crash
  if [ "$guard" = "git-branch-create" ]; then
    case "${ts:-}" in '' | *[!0-9]*) ts="" ;; esac  # digits-only -- never reaches arithmetic otherwise
    if [ -n "$ts" ] && [ "${#ts}" -gt 10 ]; then ts=""; fi  # bound magnitude -- 10 digits covers epoch seconds until year 2286; robustness hardening (bash arithmetic silently wraps an oversized literal rather than erroring), not a bypass fix -- anyone who can write ts already controls the marker file
    if [ -n "$ts" ]; then
      ts=$((10#$ts))  # force base-10 -- a leading-zero epoch would otherwise be misread as octal
      delta=$((now - ts))
      if [ "$delta" -ge 0 ] && [ "$delta" -le 60 ]; then
        allowed=true
      fi
    fi
    rm -f "$MARKER" || true # consume as soon as seen -- single use, regardless of whether this call turns out to match below; `|| true` so a read-only/permission-restricted .git/ can't turn this into a session-wide lockout via the ERR trap above
  fi
fi

# git(\.exe)? also catches the literal `git.exe` invocation PowerShell callers sometimes use.
# The repeating group catches zero or more interposed global options -- see
# this script's header comment for why it must repeat and be case-insensitive
# on -C/-c.
GIT_PREFIX='(^|[;&|]|[[:space:]])git(\.exe)?([[:space:]]+(-[Cc][[:space:]]+[^[:space:]]+|--?[^[:space:]]+))*[[:space:]]+'
# Herestring, not `echo "$COMMAND" | grep -qE ...` -- under `pipefail`, a
# large-enough $COMMAND can SIGPIPE `echo` when `grep -q` exits on an early
# match, and pipefail then reports that non-zero exit even though grep
# matched -- an `if`/`elif` condition is exempt from `set -e` aborting on
# that, so a real match would silently read as "no match" and fall through
# to allow. See issue #87; guard-raw-pr-review.sh already uses this fix.
# Residual: if the herestring redirection itself fails (unwritable/full
# $TMPDIR), grep never runs and the condition reads as "no match" -> allow.
# Not caught by the ERR trap (if-conditions are exempt) -- same class as the
# pipe form's own fork-failure path, not a regression from it.
MATCH=false
if grep -qE "${GIT_PREFIX}checkout([[:space:]]+-[^[:space:]]+)*[[:space:]]+-[bB]([[:space:]]|\$)" <<< "$COMMAND"; then
  MATCH=true
elif grep -qE "${GIT_PREFIX}switch([[:space:]]+-[^[:space:]]+)*[[:space:]]+(-[cC]|--create)([[:space:]]|\$)" <<< "$COMMAND"; then
  MATCH=true
elif grep -qE "${GIT_PREFIX}worktree[[:space:]]+add([[:space:]]+-[^[:space:]]+)*[[:space:]]+-[bB]([[:space:]]|\$)" <<< "$COMMAND"; then
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
    "permissionDecisionReason": "Raw branch creation (`git checkout -b`/`git switch -c`/`git worktree add -b`) is blocked by git-kit's branch-creation guard. Use the `starting-work` skill (`Skill(git-kit:starting-work)`) instead -- it syncs main, validates the branch name, and asks worktree-vs-branch, all of which this raw invocation would skip. If this fired from inside starting-work itself, its marker-write step is missing or ran too late -- the marker must be written immediately before this command."
  }
}
EOF
exit 0
