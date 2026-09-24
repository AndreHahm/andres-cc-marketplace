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

# Diagnostics (issue #373/#83): best-effort logging to a gitignored, per-repo file -- never to
# stdout, which is this hook's exclusive JSON-decision channel. The `start` line below and the
# `trap ... EXIT` handler together bracket every normal completion path -- an explicit `exit 0`
# anywhere in this file, the ERR trap's own `exit 0` inside fail_closed_deny, or simply reaching
# the end of the script all trigger an EXIT trap uniformly (verified live: exiting from within the
# ERR trap's own handler does still fire it), so this doesn't need hand-instrumenting every
# individual exit point. What it CANNOT catch, also verified live via a killed-subprocess test: an
# unblockable kill (this hook's own timeout, or an OS-level SIGKILL) and an interpreter that never
# launches at all -- both leave a `start` line with no matching `finish` line, which is itself the
# diagnostic signal a future investigation into #373's still-unconfirmed root cause needs. A
# failure to write here (e.g. a read-only .git) is silently ignored -- this is diagnostics, not a
# security boundary, and must never itself change this guard's own allow/deny behavior.
# Disclosed tradeoff (hook-reviewer pass): this log has no size cap or rotation -- it grows for as
# long as the repo exists. Accepted deliberately rather than adding rotation logic to a security
# guard's own hot path; a stale/oversized log is a housekeeping concern, not a correctness or
# security one, and can be cleared manually if it ever becomes large enough to matter.
DIAG_LOG="$GIT_DIR/git-kit-guard-diagnostics.log"
DIAG_GUARD_NAME="${0##*/}"  # no external process (unlike `basename "$0"`), so this can't itself fail
# `[ ! -L "$DIAG_LOG" ]` rejects the path outright if it's a symlink -- `[ -f "$DIAG_LOG" ]` alone
# dereferences a symlink and tests the FINAL target's type, so a symlink to a regular file passed
# `-f` and a dangling symlink passed `! -e`, both following the link and appending to whatever
# arbitrary file it points at instead of staying inside the repo (Codex finding, PR #380 round 8,
# live-verified: a symlinked `$DIAG_LOG` pointing outside the repo received both diagnostic lines
# from an unrelated benign command). Rejecting any FIFO or other non-regular-file target this path
# might resolve to (not just a symlink) still matters too -- opening it for append could block
# indefinitely, and combined with this hook's `onError: "warn"` timeout, that turns the guarded
# operation into a fail-open bypass (Codex finding, PR #380 round 7). Live-verified: an `mkfifo`'d
# path and a symlinked path both skip the write instantly instead of hanging/following; a regular/
# nonexistent path still logs normally.
if [ ! -L "$DIAG_LOG" ] && { [ ! -e "$DIAG_LOG" ] || [ -f "$DIAG_LOG" ]; }; then
  { printf '%s guard=%s event=start\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$DIAG_GUARD_NAME" >> "$DIAG_LOG" || true; } 2>/dev/null
fi
# `rc=$?` is captured FIRST, on its own statement -- a command substitution later in the same
# printf argument list (the `$(date ...)` call) would otherwise overwrite `$?` before `"$?"` is
# ever read, silently logging date's own exit status instead of this script's real one.
# A named function, not an inline `trap '...' EXIT` string -- ShellCheck's SC2154 ("rc is
# referenced but not assigned") can't track an assignment made inside a trap's own single-quoted
# argument, even though `rc=$?` genuinely runs before `"$rc"` is read there; a real function
# resolves this cleanly since `local rc=$?` and its later use are both ordinary statements in the
# same scope (Codacy, PR #380).
guard_diag_log_finish() {
  local rc=$?
  if [ ! -L "$DIAG_LOG" ] && { [ ! -e "$DIAG_LOG" ] || [ -f "$DIAG_LOG" ]; }; then
    { printf '%s guard=%s event=finish exit=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$DIAG_GUARD_NAME" "$rc" >> "$DIAG_LOG" || true; } 2>/dev/null
  fi
}
trap guard_diag_log_finish EXIT

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
    # `if ! rm -f ...; then ...` -- not the earlier `rm -f "$MARKER" || true` --
    # so a genuinely failed deletion (e.g. .git becomes read-only/permission-
    # restricted after the marker was written, the marker file itself still
    # readable) withholds authorization instead of trusting a marker we
    # couldn't actually consume. The old `|| true` form let `allowed` stay
    # `true` from the check above while the marker stayed on disk unconsumed,
    # so a later matching command within the remaining TTL could also be
    # authorized by the same once-intended marker -- found independently by
    # both Devin and Codex on guard-raw-destructive-cleanup.sh (PR #177), same
    # pattern here. An `if` construct is itself exempt from `set -e`/the ERR
    # trap, so this closes the gap without reopening the session-wide-lockout
    # risk the original `|| true` existed to prevent. See
    # guard-raw-destructive-cleanup.sh's own copy of this fix for the fuller
    # rationale and the one residual it explicitly leaves open.
    if ! rm -f "$MARKER"; then
      allowed=false
    fi
  fi
fi

# git(\.exe)? also catches the literal `git.exe` invocation PowerShell callers sometimes use.
# The repeating group catches zero or more interposed global options -- see
# this script's header comment for why it must repeat and be case-insensitive
# on -C/-c.
# Negated-identifier prefix class, not an enumerated one -- the old
# `(^|[;&|]|[[:space:]])` boundary missed `$(`, a backtick, and a
# path-qualified invocation's `/` (e.g. `/usr/bin/git checkout -b`), letting
# each bypass this guard with no marker check. `[^[:alnum:]_.-]` admits any
# of those as a valid boundary while still excluding `.`/`-` specifically,
# so "git" appearing mid-identifier (e.g. inside "api.github.com") is never
# mistaken for an invocation start. The optional `['"]?` right after
# `(\.exe)?` tolerates a PowerShell quoted-path invocation's closing quote
# (`& 'C:\...\git.exe' checkout -b`) landing between the executable name and
# the required whitespace. See issue #85.
# Tradeoff, accepted: widening the boundary this way also makes a quoted
# textual *mention* of the guarded command (e.g. `grep -r "git commit" ./`)
# indistinguishable from an invocation, since a quote is just another
# non-identifier character -- such a mention now denies too. Fail-safe in
# direction; a real behavior change from before, worth knowing if a
# grep/rg call over this exact literal starts unexpectedly denying.
GIT_PREFIX='(^|[^[:alnum:]_.-])git(\.exe)?['"'"'"]?([[:space:]]+(-[Cc][[:space:]]+[^[:space:]]+|--?[^[:space:]]+))*[[:space:]]+'
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
# Trailing boundaries widened the same way as GIT_PREFIX's own leading one
# (issue #85): an argument-less invocation (no branch name) left a `` ` ``/
# `)` immediately after `-b`/`-c` with no trailing whitespace, which the old
# `([[:space:]]|$)` didn't recognize as a boundary.
MATCH=false
if grep -qE "${GIT_PREFIX}checkout([[:space:]]+-[^[:space:]]+)*[[:space:]]+-[bB]([^[:alnum:]_.-]|\$)" <<< "$COMMAND"; then
  MATCH=true
elif grep -qE "${GIT_PREFIX}switch([[:space:]]+-[^[:space:]]+)*[[:space:]]+(-[cC]|--create)([^[:alnum:]_.-]|\$)" <<< "$COMMAND"; then
  MATCH=true
elif grep -qE "${GIT_PREFIX}worktree[[:space:]]+add([[:space:]]+-[^[:space:]]+)*[[:space:]]+-[bB]([^[:alnum:]_.-]|\$)" <<< "$COMMAND"; then
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
    "permissionDecisionReason": "Raw branch creation (`git checkout -b`/`git switch -c`/`git worktree add -b`) is blocked by git-kit's branch-creation guard. Use the `starting-work` skill (`Skill(git-kit:starting-work)`) instead -- it syncs main, validates the branch name, and asks worktree-vs-branch, all of which this raw invocation would skip. If this fired from inside starting-work itself, its marker-write step is missing or ran too late -- the marker must be written immediately before this command. If this was a textual mention of the command (a grep/rg search pattern, a heredoc, a doc string) rather than an actual invocation, this guard cannot distinguish the two -- reword the literal or use `Read`/`Grep` instead of a shell search."
  }
}
EOF
exit 0
