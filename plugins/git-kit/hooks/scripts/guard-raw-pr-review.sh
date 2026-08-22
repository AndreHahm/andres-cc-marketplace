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
# default for any `gh api graphql` invocation *whose command text this hook
# can actually see* -- an earlier revision of this file tried to carve out a
# narrow "verifiably read-only inline `reviewThreads` lookup, no `mutation`
# keyword, no indirection marker" exception instead, but that carve-out was
# substring matching against the raw command string, and substring matching
# a shell command string for safety is not a defensible security boundary:
# three independent reviewers (a live security-reviewer dispatch, then Codex
# and CodeRabbit on the resulting PR) each found a *different* way to make
# the literal substrings "reviewThreads"/"mutation" say something other than
# what the command actually executes -- `-F query=@file`/`$(cmd)`/backtick/
# `--input <file>` indirection, a plain shell variable holding the query
# (`gh api graphql -f query="$var"`), and adjacent-quote string concatenation
# splitting the literal word "mutation" across a quote boundary
# (`query='mut'"ation ..."`) so it never appears as a contiguous substring.
# Each fix closed one shape and the next reviewer found another -- the
# carve-out was removed rather than patched a fifth time. This means the
# `reviewThreads` read-only lookup now also requires the marker handshake,
# same as the mutation -- see `references/github-api-mechanics.md`'s
# "Resolving a review thread" section for the updated marker-timing guidance.
# **This is not a claim of unconditional coverage.** This file previously
# described a "known, disclosed residual" for a raw `gh api .../pulls/*`
# write call outside the two shapes this file guards; that residual is
# unchanged by this edit. Two more residuals apply specifically to the
# `gh api graphql` branch and are tracked in issue #85 (this repo's issue
# tracker), not fixed here: (1) the shared command-word prefix class below
# (`(^|[;&|]|[[:space:]])`) doesn't recognize `$(`, a backtick, or a quote
# character as a valid boundary, so `tid=$(gh api graphql -f query=...)` or
# `` `gh api graphql ...` `` bypasses every branch in this file, not just
# this one -- the same gap as the four sibling guard scripts' own subcommand
# matching; (2) a `gh api graphql` call reached through a script file this
# hook never inspects (e.g. `bash some-script.sh`, where the script's own
# body runs `gh api graphql` internally) is invisible to this guard by
# construction, since the tool call's own command text never contains the
# literal words this file matches on.
# A third residual, surfaced by a security-reviewer pass on 2026-08-22 while
# adding handling-review-findings's new `gh pr comment` trigger-post call
# (unrelated to the two above): the `git rev-parse --git-dir` check just
# below allows unconditionally when it finds no repository, before any
# subcommand match runs -- but every command this file guards, including
# `gh pr comment -R "<owner>/<repo>"` and the `gh api repos/{owner}/{repo}/...`
# shapes, works fine outside a local git repo, so "not in a git repo --
# nothing to guard" doesn't actually hold for this file's own guarded
# commands. Deliberately left unfixed here: this ordering is shared by the
# sibling guard scripts too, and reordering it deserves its own dedicated
# review rather than a side effect of one skill's narrower feature change.
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
# `api` DOES have to sit immediately after `gh` -- verified against `gh --help`/`gh api --help`
# (2026-08-21): `gh`'s root command has no persistent flags besides `--help`/`--version`, and `gh
# api` itself has no `-R`/`--repo` flag either, so there is no real `gh <flag> api ...` invocation
# for a widened prefix to defend against. A prior revision of this line widened the prefix to
# tolerate flags there anyway, on an unverified assumption about `gh`'s flag placement -- that
# widening was itself a regression (it dropped bare-whitespace/`env`-prefixed/indented `gh api ...`
# as valid prefixes) fixing a bypass that didn't actually exist. Reverted to the original,
# narrower form below.
API_RE='(^|[;&|]|[[:space:]])gh(\.exe)?[[:space:]]+api([[:space:]]|$)'
# Boundary classes below are "not alnum/underscore" (leading) and "not alnum/underscore/hyphen"
# (trailing), not the narrower "whitespace or /" used previously -- a quoted endpoint
# (`gh api "repos/.../replies"`, single-quoted, or the trailing `)`/backtick of a `$(...)`/
# backtick command substitution) has a quote/paren/backtick character immediately before or after
# the endpoint text, which the narrower classes didn't treat as a valid boundary, letting a quoted
# invocation bypass both branches entirely despite being a completely ordinary way to write one of
# these commands.
REPLIES_RE='(^|[^[:alnum:]_])repos/[^[:space:]]+/pulls/[^[:space:]]+/comments/[^[:space:]]+/replies([^[:alnum:]_-]|$)'
GRAPHQL_RE='(^|[^[:alnum:]_])graphql([^[:alnum:]_-]|$)'
if echo "$COMMAND" | grep -qE '(^|[;&|]|[[:space:]])gh(\.exe)?[[:space:]]+pr[[:space:]]+review([[:space:]]|$)'; then
  GH_SUBCOMMAND="gh pr review"
elif echo "$COMMAND" | grep -qE '(^|[;&|]|[[:space:]])gh(\.exe)?[[:space:]]+pr[[:space:]]+comment([[:space:]]|$)'; then
  GH_SUBCOMMAND="gh pr comment"
elif echo "$COMMAND" | grep -qE "$API_RE" && echo "$COMMAND" | grep -qE "$REPLIES_RE"; then
  GH_SUBCOMMAND="gh api .../comments/{id}/replies"
elif echo "$COMMAND" | grep -qE "$API_RE" && echo "$COMMAND" | grep -qE "$GRAPHQL_RE"; then
  # Unconditional deny-by-default -- no read-only carve-out. See this file's header comment for
  # why: a substring-matching carve-out here was tried and independently defeated by 3 different
  # reviewers using 4 different techniques, so every `gh api graphql` call is guarded now,
  # including a genuine read-only `reviewThreads` lookup.
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
