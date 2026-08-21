#!/bin/bash
# PreToolUse guard: hard-blocks a raw `gh pr review`, `gh pr comment`, or the
# two equivalent inline-review-thread `gh api` write actions (a reply to a
# review comment, or the GraphQL `resolveReviewThread` mutation) when the
# call wasn't immediately preceded by collaborating-on-a-pr's,
# explain-pr-changes's, codex-review-recovery's, or
# handling-review-findings's marker handshake. Same mechanism as
# guard-raw-pr-ops.sh (see that script's header comment for the full
# marker-handshake rationale).
#
# Deliberately narrow: `gh pr view` (read-only) and `gh pr edit` (used for
# non-review metadata edits across several skills) are NOT guarded here --
# only write actions a git-kit skill actually owns. The two `gh api` branches
# below check "is this an api call" and "does the endpoint/keyword appear
# anywhere in the command" as independent conditions (not "does the endpoint
# sit immediately after `api`") specifically because `gh api` accepts flags
# between `api` and the endpoint, and accepts a leading `/` -- see each
# branch's own inline comment for the reasoning and the reachable-by-accident
# invocations this guards against. The `gh api graphql` branch denies by
# default and only carves out the narrow, verifiably-read-only case (an
# inline `reviewThreads` lookup with no `mutation` keyword anywhere in the
# command) as unguarded -- a file/`$(cat ...)`-supplied mutation body, which
# this string-only check cannot inspect, is guarded rather than assumed safe.
# This narrows, but does not fully close, the gap this file's header
# previously described as a "known, disclosed residual" for
# handling-review-findings's two specific endpoints; a raw `gh api .../pulls/*`
# write call outside these two shapes remains unguarded, mitigated only by
# every git-kit skill with a broader `gh api` grant being a reviewed,
# allowlisted component.
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
    "permissionDecisionReason": "git-kit's reviewer-action guard requires `jq`, which isn't available in this environment -- install jq or this guard cannot verify the command is safe."
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
# match below -- not just on the call that turns out to match. See
# guard-raw-destructive-cleanup.sh's header comment for the full rationale
# (consuming only inside the match branch let a marker survive its full 60s
# TTL through any number of intervening non-matching commands). Only a marker
# whose `guard` field is this guard's own type ("gh-pr-review") is touched --
# a marker written for a sibling guard is left alone.
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || exit 0 # not in a git repo -- nothing to guard
MARKER="$GIT_DIR/git-kit-marker.txt"

now=$(date +%s)
allowed=false

if [ -f "$MARKER" ]; then
  read -r guard ts _skill < "$MARKER" || true
  guard="${guard:-}"  # defensive: a concurrent/partial read under `set -u` must degrade to "no marker", never crash
  if [ "$guard" = "gh-pr-review" ]; then
    case "${ts:-}" in '' | *[!0-9]*) ts="" ;; esac  # digits-only -- never reaches arithmetic otherwise
    if [ -n "$ts" ] && [ $((now - ts)) -le 60 ]; then
      allowed=true
    fi
    rm -f "$MARKER" # consume as soon as seen -- single use, regardless of whether this call turns out to match below
  fi
fi

GH_SUBCOMMAND=""
# gh(\.exe)? also catches the literal `gh.exe` invocation PowerShell callers sometimes use.
# The two `gh api` branches below deliberately check "is this an api call" and "does the
# endpoint/keyword appear anywhere in the command" as two INDEPENDENT conditions, unlike the
# `pr review`/`pr comment` branches above, which can safely require the subcommand word to sit
# immediately after `gh` -- `gh` requires those subcommand words adjacent, but `gh api` accepts
# flags (`-X POST`, `-H ...`) between `api` and the endpoint, and accepts the endpoint with or
# without a leading `/` or a full `https://api.github.com/...` prefix. A single combined regex
# expecting the endpoint immediately after `api` misses all of those, letting a perfectly
# ordinary `gh api -X POST repos/.../replies` invocation fall through unguarded.
API_RE='(^|[;&|]|[[:space:]])gh(\.exe)?[[:space:]]+api([[:space:]]|$)'
REPLIES_RE='(^|[[:space:]]|/)repos/[^[:space:]]+/pulls/[^[:space:]]+/comments/[^[:space:]]+/replies([[:space:]]|$)'
GRAPHQL_RE='(^|[[:space:]]|/)graphql([[:space:]]|$)'
if echo "$COMMAND" | grep -qE '(^|[;&|]|[[:space:]])gh(\.exe)?[[:space:]]+pr[[:space:]]+review([[:space:]]|$)'; then
  GH_SUBCOMMAND="gh pr review"
elif echo "$COMMAND" | grep -qE '(^|[;&|]|[[:space:]])gh(\.exe)?[[:space:]]+pr[[:space:]]+comment([[:space:]]|$)'; then
  GH_SUBCOMMAND="gh pr comment"
elif echo "$COMMAND" | grep -qE "$API_RE" && echo "$COMMAND" | grep -qE "$REPLIES_RE"; then
  GH_SUBCOMMAND="gh api .../comments/{id}/replies"
elif echo "$COMMAND" | grep -qE "$API_RE" && echo "$COMMAND" | grep -qE "$GRAPHQL_RE"; then
  # Deny-by-default for `gh api graphql`, not "deny only if the command string literally
  # contains resolveReviewThread": the mutation's `query`/`-F query=@file`/`$(cat ...)`-supplied
  # body may not appear in the command string at all, so absence of that substring can never be
  # trusted to mean read-only. Only the narrow, verifiably-read-only case -- an inline
  # `reviewThreads` lookup with no `mutation` keyword anywhere in the command -- is let through
  # unguarded; everything else (including a file-supplied body this check can't inspect) is
  # guarded, which fails closed rather than open.
  if echo "$COMMAND" | grep -q 'reviewThreads' && ! echo "$COMMAND" | grep -q 'mutation'; then
    exit 0
  fi
  GH_SUBCOMMAND="gh api graphql"
else
  exit 0
fi

if [ "$allowed" = true ]; then
  exit 0
fi

REASON="Raw \`$GH_SUBCOMMAND\` is blocked by git-kit's reviewer-action guard. Use whichever of \`collaborating-on-a-pr\`, \`explain-pr-changes\`, \`codex-review-recovery\`, or \`handling-review-findings\` matches what you're doing instead -- each writes the marker this guard requires immediately before running the same command. If this fired from inside one of those skills, its marker-write step is missing or ran too late -- the marker must be written immediately before this command."

jq -n --arg reason "$REASON" \
  '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
exit 0
