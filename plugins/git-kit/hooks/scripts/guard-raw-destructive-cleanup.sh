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
    "permissionDecisionReason": "git-kit's destructive-cleanup guard failed unexpectedly and could not verify the command is safe -- denying by default rather than allowing it through unguarded."
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
# Negated-identifier prefix class, not an enumerated one -- the old
# `(^|[;&|]|[[:space:]])` boundary missed `$(`, a backtick, and a
# path-qualified invocation's `/` (e.g. `/usr/bin/git branch -D main`),
# letting each bypass this guard with no marker check. `[^[:alnum:]_.-]`
# admits any of those as a valid boundary while still excluding `.`/`-`
# specifically, so "git" appearing mid-identifier (e.g. inside
# "api.github.com") is never mistaken for an invocation start. The optional
# `['"]?` right after `(\.exe)?` tolerates a PowerShell quoted-path
# invocation's closing quote (`& 'C:\...\git.exe' branch -D main`) landing
# between the executable name and the required whitespace. See issue #85.
# Tradeoff, accepted: widening the boundary this way also makes a quoted
# textual *mention* of the guarded command (e.g. `grep -r "git commit" ./`)
# indistinguishable from an invocation, since a quote is just another
# non-identifier character -- such a mention now denies too. Fail-safe in
# direction; a real behavior change from before, worth knowing if a
# grep/rg call over this exact literal starts unexpectedly denying.
GIT_PREFIX='(^|[^[:alnum:]_.-])git(\.exe)?['"'"'"]?([[:space:]]+(-[Cc][[:space:]]+[^[:space:]]+|--?[^[:space:]]+))*[[:space:]]+'

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
    if [ -n "$ts" ] && [ "${#ts}" -gt 10 ]; then ts=""; fi  # bound magnitude -- 10 digits covers epoch seconds until year 2286; robustness hardening (bash arithmetic silently wraps an oversized literal rather than erroring), not a bypass fix -- anyone who can write ts already controls the marker file
    if [ -n "$ts" ]; then
      ts=$((10#$ts))  # force base-10 -- a leading-zero epoch would otherwise be misread as octal
      delta=$((now - ts))
      if [ "$delta" -ge 0 ] && [ "$delta" -le 60 ]; then
        allowed=true
      fi
    fi
    rm -f "$MARKER" || true # consume as soon as seen -- single use, regardless of whether this call turns out to MATCH below; `|| true` so a read-only/permission-restricted .git/ can't turn this into a session-wide lockout via the ERR trap above
  fi
fi

MATCH=false

# `git branch -D <name>` (or the equivalent `-d -f`/`-f -d`/`-df`/`-fd`/
# `--delete --force` spellings) -- only when <name> is one of the protected
# patterns. <name> may optionally be quoted -- `git-cleanup/SKILL.md` itself
# instructs quoting the branch variable, so an unquoted-only match would miss
# the exact form that skill is told to write.
DELETE_FLAG='(-D|--delete[[:space:]]+--force|--force[[:space:]]+--delete|-d[[:space:]]+-f|-f[[:space:]]+-d|-df|-fd)'
# Herestring, not `echo "$COMMAND" | grep -qE ...` -- under `pipefail`, a
# large-enough $COMMAND can SIGPIPE `echo` when `grep -q` exits on an early
# match, and pipefail then reports that non-zero exit even though grep
# matched -- an `if` condition is exempt from `set -e` aborting on that, so
# a real match would silently read as "no match" and fall through to allow.
# See issue #87; guard-raw-pr-review.sh already uses this fix.
# Residual: if the herestring redirection itself fails (unwritable/full
# $TMPDIR), grep never runs and the condition reads as "no match" -> allow.
# Not caught by the ERR trap (if-conditions are exempt) -- same class as the
# pipe form's own fork-failure path, not a regression from it.
# Trailing boundary widened the same way as GIT_PREFIX's own leading one
# (issue #85): an argument-less `` `git branch -D main` ``/`$(...)` left a
# `` ` ``/`)` immediately after the protected-branch name with no trailing
# whitespace, which the old `([[:space:]]|$)` didn't recognize as a
# boundary -- found via a security-reviewer pass on this same fix, live-
# verified as a real bypass before this line existed.
if grep -qE "${GIT_PREFIX}branch([[:space:]]+-[^[:space:]]+)*[[:space:]]+${DELETE_FLAG}([[:space:]]+-[^[:space:]]+)*[[:space:]]+[\"']?(main|master|develop|release/[^[:space:]\"']*)[\"']?([^[:alnum:]_.-]|\$)" <<< "$COMMAND"; then
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
# Same negated-identifier boundary class as GIT_PREFIX above, on both ends --
# WORKTREE_REMOVE_SPANS (below) captures up to the next `;`/`&`/`|` or end of
# string, but a command wrapped in `$(...)`/backticks leaves a trailing `)`/
# `` ` `` right after --force/-f, which the old `([[:space:]]|$)` trailing
# boundary didn't recognize as a boundary at all -- found via this issue's
# own live testing: `git worktree remove foo --force` wrapped in backticks
# still bypassed this guard even after the GIT_PREFIX fix below. See issue #85.
FORCE_FLAG_RE='(^|[^[:alnum:]_.-])(--force|-f)([^[:alnum:]_.-]|$)'
# The `-oE` extraction below stays a pipe, not a herestring -- `grep -o`
# reads to EOF rather than exiting on first match, so it has no SIGPIPE
# exposure (issue #87 doesn't apply here); the `-qE` check just below it
# does, and uses a herestring for the same reason as the branch -D check
# above (residual: same undocumented herestring-failure fail-open as noted
# there, not caught by the ERR trap).
WORKTREE_REMOVE_SPANS=$(echo "$COMMAND" | grep -oE "${GIT_PREFIX}worktree[[:space:]]+remove[^;&|]*" || true)
if [ -n "$WORKTREE_REMOVE_SPANS" ] && grep -qE "$FORCE_FLAG_RE" <<< "$WORKTREE_REMOVE_SPANS"; then
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
    "permissionDecisionReason": "Raw `git branch -D` targeting a protected branch (main/master/develop/release/*), or raw `git worktree remove --force`, is blocked by git-kit's destructive-cleanup guard. Use the `git-cleanup` skill (`/git-cleanup`) instead -- it gates these irreversible actions behind explicit user confirmation. If this fired from inside git-cleanup itself, its marker-write step is missing or ran too late -- the marker must be written immediately before this command. If this was a textual mention of the command (a grep/rg search pattern, a heredoc, a doc string) rather than an actual invocation, this guard cannot distinguish the two -- reword the literal or use `Read`/`Grep` instead of a shell search."
  }
}
EOF
exit 0
