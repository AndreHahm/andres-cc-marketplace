#!/bin/bash
# PreToolUse guard: hard-blocks a raw `git commit` invocation that wasn't
# immediately preceded by an allowlisted git-kit skill's marker handshake.
#
# Marker handshake: a skill that legitimately runs `git commit` directly
# (commit, standalone-commits) writes a single line "git-commit <epoch> <skill>"
# to $(git rev-parse --git-dir)/git-kit-marker.txt right before running it.
# This hook consumes a marker matching its own guard type ("git-commit") on
# every Bash/PowerShell call, before checking whether the current command
# actually matches -- so a marker can't survive its full 60s TTL untouched
# through intervening unrelated commands, and can't be reused for a second,
# unrelated raw command later in the session. A marker for a different guard
# type is left untouched.
#
# The marker lives under .git/ (never .claude/) specifically so it can never
# be accidentally committed regardless of a consuming project's .gitignore --
# .git/ itself is never tracked, by git's own design.
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
    "permissionDecisionReason": "git-kit's commit guard failed unexpectedly and could not verify the command is safe -- denying by default rather than allowing it through unguarded."
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
    "permissionDecisionReason": "git-kit's raw-command guard requires `jq`, which isn't available in this environment -- install jq or this guard cannot verify the command is safe."
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
# whose `guard` field is this guard's own type ("git-commit") is touched --
# a marker written for a sibling guard is left alone.
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || exit 0  # not in a git repo -- nothing to guard
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
# `[ -f "$DIAG_LOG" ]` (which dereferences a symlink and tests the final target's type) guards
# every write below -- if the path exists but isn't a regular file (e.g. a FIFO planted by an
# attacker), opening it for append could block indefinitely, and combined with this hook's
# `onError: "warn"` timeout, that turns the guarded operation into a fail-open bypass (Codex
# finding, PR #380). Live-verified: an `mkfifo`'d path skips the write instantly instead of
# hanging; a regular/nonexistent path still logs normally.
if [ ! -e "$DIAG_LOG" ] || [ -f "$DIAG_LOG" ]; then
  { printf '%s guard=%s event=start\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$DIAG_GUARD_NAME" >> "$DIAG_LOG" || true; } 2>/dev/null
fi
# `rc=$?` is captured FIRST, on its own statement -- a command substitution later in the same
# printf argument list (the `$(date ...)` call) would otherwise overwrite `$?` before `"$?"` is
# ever read, silently logging date's own exit status instead of this script's real one.
trap 'rc=$?; if [ ! -e "$DIAG_LOG" ] || [ -f "$DIAG_LOG" ]; then { printf "%s guard=%s event=finish exit=%s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$DIAG_GUARD_NAME" "$rc" >> "$DIAG_LOG" || true; } 2>/dev/null; fi' EXIT

now=$(date +%s)
allowed=false

if [ -f "$MARKER" ]; then
  read -r guard ts _skill < "$MARKER" || true
  guard="${guard:-}"  # defensive: a concurrent/partial read under `set -u` must degrade to "no marker", never crash
  if [ "$guard" = "git-commit" ]; then
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

# Match `git commit` as a standalone subcommand invocation -- not a mention of
# the word "commit" elsewhere (e.g. `git log --grep=commit`, `echo "commit this"`).
# `git(\.exe)?` also catches the literal `git.exe` invocation PowerShell callers
# sometimes use. The repeating group catches zero or more interposed global
# options -- `-C <dir>`/`-c <k>=<v>` (each a separate space-delimited value
# token) or any other single-token `-`/`--` flag (e.g. `--no-pager`) -- so
# stacked options like `git -c a=b -c c=d commit` or `git --no-pager commit`
# can't bypass this guard. Same prefix pattern guard-raw-branch-create.sh
# already uses.
# Negated-identifier prefix class, not an enumerated one -- the old
# `(^|[;&|]|[[:space:]])` boundary missed `$(`, a backtick, and a
# path-qualified invocation's `/` (e.g. `/usr/bin/git commit`), letting each
# bypass this guard with no marker check. `[^[:alnum:]_.-]` admits any of
# those as a valid boundary while still excluding `.`/`-` specifically, so
# "git" appearing mid-identifier (e.g. inside "api.github.com") is never
# mistaken for an invocation start. The optional `['"]?` right after
# `(\.exe)?` tolerates a PowerShell quoted-path invocation's closing quote
# (`& 'C:\...\git.exe' commit`) landing between the executable name and the
# required whitespace. See issue #85.
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
# Trailing boundary widened the same way as GIT_PREFIX's own leading one
# (issue #85): an argument-less `` `git commit` ``/`$(git commit)` left a
# `` ` ``/`)` immediately after "commit" with no argument or trailing
# whitespace, which the old `([[:space:]]|$)` didn't recognize as a
# boundary -- found via a security-reviewer pass on this same fix, live-
# verified as a real bypass before this line existed.
if ! grep -qE "${GIT_PREFIX}commit([^[:alnum:]_.-]|\$)" <<< "$COMMAND"; then
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
    "permissionDecisionReason": "Raw `git commit` is blocked by git-kit's commit guard. Use the `commit` skill (`/commit`) instead -- it handles staging review, sensitive-file scanning, message formatting, and the behavior-change test gate this raw invocation would skip. If this fired from inside an allowlisted git-kit skill (commit, standalone-commits), its marker-write step is missing or ran too late -- the marker must be written immediately before this command, not earlier in the same run. If this was a textual mention of the command (a grep/rg search pattern, a heredoc, a doc string) rather than an actual invocation, this guard cannot distinguish the two -- reword the literal or use `Read`/`Grep` instead of a shell search."
  }
}
EOF
exit 0
