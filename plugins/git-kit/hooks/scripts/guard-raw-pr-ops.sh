#!/bin/bash
# PreToolUse guard: hard-blocks a raw `gh pr create` or `gh pr merge`
# invocation that wasn't immediately preceded by an allowlisted git-kit
# skill's marker handshake. Same mechanism as guard-raw-commit.sh (see that
# script's header comment for the full marker-handshake rationale) -- kept
# as a separate script/hook registration since it guards a different pair
# of commands and has its own guard-type values.
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
    "permissionDecisionReason": "git-kit's PR-operations guard failed unexpectedly and could not verify the command is safe -- denying by default rather than allowing it through unguarded."
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
    "permissionDecisionReason": "git-kit's PR-operations guard requires `jq`, which isn't available in this environment -- install jq or this guard cannot verify the command is safe."
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

# Consume our own marker on every Bash/PowerShell call, before the subcommand
# match below determines which of this script's two guard types actually
# applies. See guard-raw-destructive-cleanup.sh's header comment for the full
# rationale (consuming only inside the match branch let a marker survive its
# full 60s TTL through any number of intervening non-matching commands).
# Unlike the other guards, this script owns two guard types ("gh-pr-create"
# and "gh-pr-merge") -- a marker is consumed here if it belongs to EITHER of
# them (before we know which specific subcommand, if any, this call is), but
# is only treated as authorizing this call once the actual subcommand is
# known below. A marker written for a sibling guard (a different type
# entirely) is left alone.
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || exit 0  # not in a git repo -- nothing to guard
MARKER="$GIT_DIR/git-kit-marker.txt"

now=$(date +%s)
allowed=false
marker_guard=""
marker_ts=""

if [ -f "$MARKER" ]; then
  read -r guard ts _skill < "$MARKER" || true
  guard="${guard:-}"  # defensive: a concurrent/partial read under `set -u` must degrade to "no marker", never crash
  if [ "$guard" = "gh-pr-create" ] || [ "$guard" = "gh-pr-merge" ]; then
    case "${ts:-}" in '' | *[!0-9]*) ts="" ;; esac  # digits-only -- never reaches arithmetic otherwise
    if [ -n "$ts" ] && [ "${#ts}" -gt 10 ]; then ts=""; fi  # bound magnitude -- 10 digits covers epoch seconds until year 2286; robustness hardening (bash arithmetic silently wraps an oversized literal rather than erroring), not a bypass fix -- anyone who can write ts already controls the marker file
    if [ -n "$ts" ]; then
      ts=$((10#$ts))  # force base-10 -- a leading-zero epoch would otherwise be misread as octal
    fi
    marker_guard="$guard"
    marker_ts="$ts"
    # `if ! rm -f ...; then marker_ts=""; ...` -- not the earlier
    # `rm -f "$MARKER" || true` -- so a genuinely failed deletion (e.g. .git
    # becomes read-only/permission-restricted after the marker was written,
    # the marker file itself still readable) withholds authorization instead
    # of trusting a marker we couldn't actually consume. Blanking marker_ts on
    # failure reuses this file's own existing invalid-marker sentinel (see its
    # initialization above and the malformed-timestamp handling just above
    # this block) -- the later `[ -n "$marker_ts" ]` check further down
    # already treats an empty marker_ts as "no valid marker", so no new
    # variable is needed. The old `|| true` form let marker_ts/marker_guard
    # stay populated while the marker stayed on disk unconsumed, so a later
    # matching command within the remaining TTL could also be authorized by
    # the same once-intended marker -- found independently by both Devin and
    # Codex on the sibling guard-raw-destructive-cleanup.sh (PR #177), same
    # pattern here. An `if` construct is itself exempt from `set -e`/the ERR
    # trap, so this closes the gap without reopening the session-wide-lockout
    # risk the original `|| true` existed to prevent. See
    # guard-raw-destructive-cleanup.sh's own copy of this fix for the fuller
    # rationale and the one residual it explicitly leaves open.
    if ! rm -f "$MARKER"; then
      marker_ts=""
    fi
  fi
fi

GUARD_TYPE=""
SKILL_NAME=""
GH_SUBCOMMAND=""
SKILL_HANDLES=""
# gh(\.exe)? also catches the literal `gh.exe` invocation PowerShell callers sometimes use.
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
# Negated-identifier prefix class, not an enumerated one -- the old
# `(^|[;&|]|[[:space:]])` boundary missed `$(`, a backtick, and a
# path-qualified invocation's `/`, letting each bypass this guard with no
# marker check. `[^[:alnum:]_.-]` admits any of those as a valid boundary
# while still excluding `.`/`-`, so "gh" mid-identifier is never mistaken
# for an invocation start. The optional `['"]?` right after `(\.exe)?`
# tolerates a PowerShell quoted-path invocation's closing quote landing
# between the executable name and the required whitespace. See issue #85.
# Tradeoff, accepted: widening the boundary this way also makes a quoted
# textual *mention* of the guarded command (e.g. `grep -r "git commit" ./`)
# indistinguishable from an invocation, since a quote is just another
# non-identifier character -- such a mention now denies too. Fail-safe in
# direction; a real behavior change from before, worth knowing if a
# grep/rg call over this exact literal starts unexpectedly denying.
# Trailing boundary also widened the same way: an argument-less `` `gh pr
# create` ``/`$(gh pr merge)` left a `` ` ``/`)` immediately after the
# subcommand with no trailing whitespace, which the old `([[:space:]]|$)`
# didn't recognize as a boundary -- both are valid, real invocations with
# no required arguments.
if grep -qE '(^|[^[:alnum:]_.-])gh(\.exe)?['"'"'"]?[[:space:]]+pr[[:space:]]+create([^[:alnum:]_.-]|$)' <<< "$COMMAND"; then
  GUARD_TYPE="gh-pr-create"
  SKILL_NAME="create-pr"
  GH_SUBCOMMAND="gh pr create"
  SKILL_HANDLES="template resolution, draft-vs-ready confirmation, and pre-flight commit checks"
elif grep -qE '(^|[^[:alnum:]_.-])gh(\.exe)?['"'"'"]?[[:space:]]+pr[[:space:]]+merge([^[:alnum:]_.-]|$)' <<< "$COMMAND"; then
  GUARD_TYPE="gh-pr-merge"
  SKILL_NAME="merge-pr"
  GH_SUBCOMMAND="gh pr merge"
  SKILL_HANDLES="readiness checks (draft/CI/reviews) and a merge-rights verification"
else
  exit 0
fi

if [ "$marker_guard" = "$GUARD_TYPE" ] && [ -n "$marker_ts" ]; then
  delta=$((now - marker_ts))
  if [ "$delta" -ge 0 ] && [ "$delta" -le 60 ]; then
    allowed=true
  fi
fi

if [ "$allowed" = true ]; then
  exit 0
fi

REASON="Raw \`$GH_SUBCOMMAND\` is blocked by git-kit's PR-operations guard. Use the \`$SKILL_NAME\` skill (\`/$SKILL_NAME\`) instead -- it handles $SKILL_HANDLES this raw invocation would skip. If this fired from inside $SKILL_NAME itself, its marker-write step is missing or ran too late -- the marker must be written immediately before this command. If this was a textual mention of the command (a grep/rg search pattern, a heredoc, a doc string) rather than an actual invocation, this guard cannot distinguish the two -- reword the literal or use \`Read\`/\`Grep\` instead of a shell search."

jq -n --arg reason "$REASON" \
  '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
exit 0
