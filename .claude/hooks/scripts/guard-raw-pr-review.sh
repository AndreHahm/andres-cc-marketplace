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
# only write actions a git-kit skill actually owns. The three `gh api`
# branches (REPLIES_RE/REVIEWS_RE/GRAPHQL_RE) below span-extract each `gh
# api` invocation's own argument range (from `api` up to the next `;`/`&`/`|`
# or end of string, issue #116/#120-style span-bounding) and match the
# endpoint/keyword anywhere WITHIN that span (not "does the endpoint sit
# immediately after `api`") specifically because `gh api` accepts flags
# between `api` and the endpoint, and accepts a leading `/` -- see each
# branch's own inline comment for the reasoning and the reachable-by-accident
# invocations this guards against. Span-bounded, not "does an api call and
# the endpoint text each appear anywhere in the whole command" as two fully
# independent conditions -- that whole-command form was this file's own
# original design and was found to be a live, false-positive-producing bug
# (PR #177): an unrelated benign `gh api` call chained with unrelated later
# text that happened to contain an endpoint substring could combine into a
# false deny. The `gh api graphql` branch denies by
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
# write call outside the shapes this file guards. Issue #86 narrowed that
# residual: `gh api ... repos/{owner}/{repo}/pulls/{n}/reviews` (the REST
# equivalent of `gh pr review --approve`/`--request-changes`) is now guarded
# too (see REVIEWS_RE below), verb-agnostic (GET-list and POST-submit both
# denied, matching this file's existing REPLIES_RE/GRAPHQL_RE convention --
# a verb-scoped regex is itself a bypassable substring check, and `gh api`
# defaults to POST the moment any `-f`/`-F` param is present, so the
# issue's own repro carries no explicit verb token to match on at all). A
# security-reviewer pass found this reaches further than git-kit's own
# `allowed-tools` grants: `plugin-devkit`'s `rules-extract` skill
# (`Bash(gh:*)`, no git-kit marker grant) read this same endpoint via raw
# `gh api` for its PR-review-mode data collection. Fixed in the same
# change: `rules-extract` migrated to `gh pr view --json reviews` (see
# `plugins/plugin-devkit/skills/rules-extract/references/pr-review-mode.md`'s
# Step P3), which this guard never touches. Verified two ways, not one: an
# instruction-level grep for the literal endpoint string across every
# plugin's actual documented commands (not just its `allowed-tools` grant
# list) found `rules-extract` as the only Claude-Code-executed component
# that actually issued this call -- a broad grant alone doesn't mean a
# conflict, since several other components (`extract-rules`/`apply-rules`
# commands, `rules-apply`, git-kit's own `codex-review-recovery`) hold a
# blanket `Bash(gh:*)`/`Bash(gh api *)`/`Bash(gh api:*)` grant reaching this
# endpoint but never instruct a call to it. gh-operations' own quality gate
# separately confirms the write side specifically was already a known,
# deliberately-avoided conflict before this change ("cannot be scoped
# narrower than the merge/review write paths it would also reach").
# **Deliberately still unguarded**, unlike the above: `gh api ...
# repos/{owner}/{repo}/issues/{n}/comments` (the REST equivalent of
# `gh pr comment`, since PRs share the Issues API for comments) -- issue
# #86 also named this endpoint, but both `gh-operations`
# (`Bash(gh api repos/*/issues:*)`, with a documented example using exactly
# this endpoint) and `github-issue-lifecycle`
# (`Bash(gh api repos/*/issues/*:*)`, broader still) already have a
# legitimate, currently-functioning grant reaching it for genuine
# issue-commenting -- and a PR number and an issue number share the same ID
# space, so "commenting on issue #45" and "commenting on PR #45" are
# syntactically identical at this endpoint; no regex can tell them apart.
# Guarding it would break those two skills' existing functionality, not
# just close a gap. Left open by explicit decision (2026-08-28), not an
# oversight -- closing it needs a coordinated fix across those two skills
# (a marker handshake, or switching their raw `gh api` usage to
# `gh issue comment`) before this file can safely guard the endpoint too.
# Out of scope by construction, not by decision: `.github/workflows/
# await-codex-review.yml` also calls the reviews endpoint directly, but a
# `PreToolUse` hook only ever fires on a Claude Code tool call, never on a
# CI job step -- this guard has no way to reach it and none is needed.
# A second residual, previously tracked in issue #85
# alongside the one below, is now fixed: the shared command-word prefix
# class (below, and in this file's other two `gh` matches) is now a
# negated-identifier class (`(^|[^[:alnum:]_.-])`) that recognizes `$(`, a
# backtick, a path-qualified invocation's `/`, and a PowerShell quoted-path
# invocation's closing quote as valid boundaries -- closing the
# `tid=$(gh api graphql -f query=...)` / `` `gh api graphql ...` `` bypass
# this file and the four sibling guard scripts previously shared. One
# residual from issue #85 remains open, tracked there still: a `gh api
# graphql` call reached through a script file this hook never inspects
# (e.g. `bash some-script.sh`, where the script's own body runs `gh api
# graphql` internally) stays invisible to this guard by construction, since
# the tool call's own command text never contains the literal words this
# file matches on -- no regex change can close that gap.
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

# Fail closed on an unexpected non-zero exit below (not the deliberate deny
# paths, and not a context set -e already exempts -- an if/while/&&/||/case
# test). Residual, not covered by this trap: a fatal expansion error (an
# unbound variable, a bad arithmetic expression) is a parse-time error bash
# treats differently from a command's exit status, and a missing/
# non-executable interpreter or a hook timeout kill are outside this script's
# control entirely -- all three still fail open under this hook's "onError":
# "warn" registration. What this trap does close: an ordinary command
# failure that would otherwise crash the script and let the guarded command
# through with no marker check at all. See issue #83. (The malformed-JSON
# case just below already has its own explicit fail-closed handling; this
# trap is defense-in-depth for any other unexpected crash in this file.)
fail_closed_deny() {
  cat <<'EOF' || true
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "git-kit's reviewer-action guard failed unexpectedly and could not verify the command is safe -- denying by default rather than allowing it through unguarded."
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
    "permissionDecisionReason": "git-kit's reviewer-action guard requires `jq`, which isn't available in this environment -- install jq or this guard cannot verify the command is safe."
  }
}
EOF
  exit 0
fi

# A malformed-JSON failure here must fail closed, not crash-then-warn: under `set -e`, an unguarded
# `jq` failure aborts the script before any explicit-deny path runs, and this hook's own "onError":
# "warn" registration then lets the guarded command through with only a warning -- the same
# fail-open shape the missing-jq-binary check above already guards against, just one step later.
INPUT=$(cat)
DENY_MALFORMED='{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "git-kit'"'"'s reviewer-action guard could not parse the tool-call input as JSON -- failing closed rather than letting a malformed-input crash silently allow the command through."
  }
}'
TOOL_NAME=$(jq -r '.tool_name // empty' <<< "$INPUT") || { echo "$DENY_MALFORMED"; exit 0; }
COMMAND=$(jq -r '.tool_input.command // empty' <<< "$INPUT") || { echo "$DENY_MALFORMED"; exit 0; }

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
    # authorized by the same once-intended marker -- this exact file/line was
    # Devin's own cited example (SEC finding, PR #177), independently
    # confirmed by Codex on the sibling guard-raw-destructive-cleanup.sh. An
    # `if` construct is itself exempt from `set -e`/the ERR trap, so this
    # closes the gap without reopening the session-wide-lockout risk the
    # original `|| true` existed to prevent. See
    # guard-raw-destructive-cleanup.sh's own copy of this fix for the fuller
    # rationale and the one residual it explicitly leaves open.
    if ! rm -f "$MARKER"; then
      allowed=false
    fi
  fi
fi

# Normalized copy of $COMMAND for every match below (pr review/pr comment, and
# the API_SPANS extraction further down) -- a backslash-continued (Bash) or
# backtick-continued (PowerShell) `gh api ...` invocation is one logical
# command but multiple lines to a line-oriented `grep`, so span extraction via
# `grep -oE` only ever saw the first line, silently missing an endpoint match
# sitting on a later line -- live-verified as a real bypass (a
# `gh api \` + newline + `-X POST \` + newline + `repos/.../reviews \` +
# newline + `-f event=APPROVE` call was allowed through entirely). Found by a
# security-reviewer pass on this same span-scoping fix (PR #177) -- the fix
# ports guard-raw-destructive-cleanup.sh's own COMMAND_FLAT normalization
# (issue #116), which that file needed for the identical reason. See that
# file's own COMMAND_FLAT definition for its own two-part rationale
# (CRLF-first stripping, per-shell continuation character). A third point is
# specific to THIS file, not documented on the sibling: bare `grep -q` on raw
# $COMMAND for the `pr review`/`pr comment` checks below was ALSO
# line-oriented and vulnerable to the same continuation-escaping gap, just
# pre-existing rather than introduced by this fix -- not previously disclosed
# anywhere in this file until now.
COMMAND_FLAT="${COMMAND//$'\r'/}"
if [ "$TOOL_NAME" = "Bash" ]; then
  COMMAND_FLAT="${COMMAND_FLAT//$'\\\n'/}"
elif [ "$TOOL_NAME" = "PowerShell" ]; then
  COMMAND_FLAT="${COMMAND_FLAT//$'`\n'/}"
fi
COMMAND_FLAT="${COMMAND_FLAT//$'\n'/;}"
# De-fang redirection operators that contain a `;`/`&`/`|` byte the API_SPANS
# terminator class below (`[^;&|]`) would otherwise mistake for a real command
# separator, narrowing (not closing) the residual noted at API_SPANS' own
# definition -- same operator set and same rationale as
# guard-raw-destructive-cleanup.sh's own copy of this fix (issue #120); see
# that file's own comment for the full per-operator coverage table.
COMMAND_FLAT="${COMMAND_FLAT//&>/ >}"
COMMAND_FLAT="${COMMAND_FLAT//>&/> }"
COMMAND_FLAT="${COMMAND_FLAT//<&/< }"
COMMAND_FLAT="${COMMAND_FLAT//>|/> }"

GH_SUBCOMMAND=""
# gh(\.exe)? also catches the literal `gh.exe` invocation PowerShell callers sometimes use.
# The `gh api` branch below span-extracts each invocation (API_SPAN_PREFIX_RE
# + API_SPANS further down) rather than checking a single combined regex,
# because `gh api` accepts flags (`-X POST`, `-H ...`) between `api` and the
# endpoint, and accepts the endpoint with or without a leading `/` or a full
# `https://api.github.com/...` prefix -- unlike `pr review`/`pr comment`
# below, which can safely require the subcommand word to sit immediately
# after `gh`. A single combined regex expecting the endpoint immediately
# after `api` misses all of those, letting a perfectly ordinary
# `gh api -X POST repos/.../replies` invocation fall through unguarded.
# `api` DOES have to sit immediately after `gh` -- verified against `gh --help`/`gh api --help`
# (2026-08-21): `gh`'s root command has no persistent flags besides `--help`/`--version`, and `gh
# api` itself has no `-R`/`--repo` flag either, so there is no real `gh <flag> api ...` invocation
# for a widened prefix to defend against. A prior revision of this line widened the prefix to
# tolerate flags there anyway, on an unverified assumption about `gh`'s flag placement -- that
# widening was itself a regression (it dropped bare-whitespace/`env`-prefixed/indented `gh api ...`
# as valid prefixes) fixing a bypass that didn't actually exist. Reverted to the original,
# narrower form, which API_SPAN_PREFIX_RE below still uses as its own leading boundary.
API_SPAN_PREFIX_RE='(^|[^[:alnum:]_.-])gh(\.exe)?['"'"'"]?[[:space:]]+api'
# Boundary classes below are "not alnum/underscore" (leading) and "not alnum/underscore/hyphen"
# (trailing), not the narrower "whitespace or /" used previously -- a quoted endpoint
# (`gh api "repos/.../replies"`, single-quoted, or the trailing `)`/backtick of a `$(...)`/
# backtick command substitution) has a quote/paren/backtick character immediately before or after
# the endpoint text, which the narrower classes didn't treat as a valid boundary, letting a quoted
# invocation bypass both branches entirely despite being a completely ordinary way to write one of
# these commands.
REPLIES_RE='(^|[^[:alnum:]_])repos/[^[:space:]]+/pulls/[^[:space:]]+/comments/[^[:space:]]+/replies([^[:alnum:]_-]|$)'
GRAPHQL_RE='(^|[^[:alnum:]_])graphql([^[:alnum:]_-]|$)'
# Matches any `gh api ... repos/{owner}/{repo}/pulls/{n}/reviews` call
# regardless of HTTP verb (GET to list, POST to submit an approve/request-
# changes/comment review) -- same unconditional-endpoint-match approach as
# REPLIES_RE/GRAPHQL_RE above, not a verb-specific check: this file's own
# `gh api graphql` branch already established that verb-agnostic matching
# is the safer default here, since a verb check is itself regex-based and
# addable-to the same bypass class this file exists to avoid. See issue #86.
REVIEWS_RE='(^|[^[:alnum:]_])repos/[^[:space:]]+/pulls/[^[:space:]]+/reviews([^[:alnum:]_-]|$)'
# Herestrings (<<<), not `echo ... | grep -q`, for every match below (now against $COMMAND_FLAT/
# $api_span, not raw $COMMAND -- see those variables' own definitions above): under
# `set -o pipefail`, a `grep -q` match found early enough to leave its input partly unread can
# SIGPIPE the `echo` that's still writing it, and pipefail then reports that non-zero exit for the
# pipeline even though grep
# itself matched -- an `if`/`elif` condition is exempt from `set -e` aborting on that, so the guard
# would just silently treat a real match as "no match" and fall through toward `else: exit 0` (allow).
# A herestring feeds the same text without a second process or a pipe, so there's nothing to SIGPIPE.
# Residual: if the herestring redirection itself fails (unwritable/full
# $TMPDIR), grep never runs and the condition reads as "no match" -> allow.
# Not caught by an ERR trap (if-conditions are exempt) -- same class as the
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
# review` ``/`$(gh pr comment)` left a `` ` ``/`)` immediately after the
# subcommand with no trailing whitespace, which the old `([[:space:]]|$)`
# didn't recognize as a boundary.
if grep -qE '(^|[^[:alnum:]_.-])gh(\.exe)?['"'"'"]?[[:space:]]+pr[[:space:]]+review([^[:alnum:]_.-]|$)' <<< "$COMMAND_FLAT"; then
  GH_SUBCOMMAND="gh pr review"
elif grep -qE '(^|[^[:alnum:]_.-])gh(\.exe)?['"'"'"]?[[:space:]]+pr[[:space:]]+comment([^[:alnum:]_.-]|$)' <<< "$COMMAND_FLAT"; then
  GH_SUBCOMMAND="gh pr comment"
else
  # Span-bound REPLIES_RE/REVIEWS_RE/GRAPHQL_RE to each individual `gh api`
  # invocation's own argument span (from `api` up to the next `;`/`&`/`|` or
  # end of string), not run independently against the whole $COMMAND string.
  # $COMMAND can legally contain multiple chained sub-commands
  # (`&&`/`;`/`|`); the previous form (a "gh ... api" prefix match ANDed with
  # a separate REVIEWS_RE/REPLIES_RE/GRAPHQL_RE match, each run against the
  # whole $COMMAND independently) checked "is there a gh api call
  # anywhere" and "does the endpoint text appear anywhere" as two fully
  # independent conditions against the same whole-string text, so an
  # unrelated, benign `gh api` call chained with unrelated later text that
  # happened to contain one of these endpoint substrings could combine into a
  # false deny -- live-verified: `gh api user; echo
  # repos/acme/project/pulls/12/reviews` (the reviews text sits in an `echo`
  # argument, not a `gh api` call at all) was denied by the old form. Found by
  # Devin's review of PR #177. Mirrors the same span-bounding fix
  # guard-raw-destructive-cleanup.sh's own BRANCH_SPANS/WORKTREE_REMOVE_SPANS
  # already use (issue #116) -- each span is checked independently, in a
  # loop, never against a concatenated multi-span blob.
  # Reads $COMMAND_FLAT, not raw $COMMAND -- a backslash/backtick-continued
  # `gh api` call is one logical command but multiple lines to a
  # line-oriented `grep -oE`, which silently missed an endpoint match sitting
  # on a later line -- a real fail-open bypass found by a security-reviewer
  # pass on this exact fix, closed by the COMMAND_FLAT normalization above.
  # Residual, same class as issue #120's already-accepted residual on the
  # sibling guard-raw-destructive-cleanup.sh: this span terminator class
  # (`[^;&|]`) still can't distinguish a real shell separator from the same
  # byte inside two related cases the COMMAND_FLAT de-fang step above doesn't
  # reach: (1) a quoted argument value placed before the endpoint text (e.g.
  # `gh api --jq '.[] | .id' repos/.../reviews`, where the quoted `|` inside
  # `--jq`'s own value truncates the span before it ever reaches the
  # endpoint), and (2) an unquoted nested construct -- `$(...)`, backticks,
  # `$((...))`, `<(...)` -- whose own body contains one of these bytes (e.g.
  # `gh api repos/o/r/pulls/$(gh pr view --json number | jq -r .number)/reviews`,
  # where the `|` inside `$(...)` truncates the span before `/reviews`, and
  # the inner `gh pr view` call itself matches none of this file's other
  # checks either) -- arguably the more likely shape in practice, since a
  # `gh api` endpoint is often built by interpolation rather than typed
  # literally. Neither case is closed here, since doing so needs real shell
  # tokenization, not a character-class cut. The enumerated redirection
  # operator set (`&>`/`&>>`/`>&`/`<&`/`>|`) IS de-fanged by the
  # COMMAND_FLAT step above, before this span is ever extracted.
  API_SPANS=$(grep -oE "${API_SPAN_PREFIX_RE}[^;&|]*" <<< "$COMMAND_FLAT" || true)
  if [ -n "$API_SPANS" ]; then
    while IFS= read -r api_span; do
      # `if [ -n ... ]` wrapping, not `[ -z ... ] && continue` -- same
      # set -e/ERR-trap exemption reasoning as BRANCH_SPANS' own loop.
      if [ -n "$api_span" ] && grep -qE "$REPLIES_RE" <<< "$api_span"; then
        GH_SUBCOMMAND="gh api .../comments/{id}/replies"
        break
      elif [ -n "$api_span" ] && grep -qE "$REVIEWS_RE" <<< "$api_span"; then
        GH_SUBCOMMAND="gh api .../pulls/{n}/reviews"
        break
      elif [ -n "$api_span" ] && grep -qE "$GRAPHQL_RE" <<< "$api_span"; then
        # Unconditional deny-by-default -- no read-only carve-out. See this file's header comment
        # for why: a substring-matching carve-out here was tried and independently defeated by 3
        # different reviewers using 4 different techniques, so every `gh api graphql` call is
        # guarded now, including a genuine read-only `reviewThreads` lookup.
        GH_SUBCOMMAND="gh api graphql"
        break
      fi
    done <<< "$API_SPANS"
  fi
  if [ -z "$GH_SUBCOMMAND" ]; then
    exit 0
  fi
fi

if [ "$allowed" = true ]; then
  exit 0
fi

REASON="Raw \`$GH_SUBCOMMAND\` is blocked by git-kit's reviewer-action guard. Use whichever of \`collaborating-on-a-pr\`, \`explain-pr-changes\`, \`codex-review-recovery\`, or \`handling-review-findings\` matches what you're doing instead -- each writes the marker this guard requires immediately before running the same command. If this fired from inside one of those skills, its marker-write step is missing or ran too late -- the marker must be written immediately before this command. If this was a textual mention of the command (a grep/rg search pattern, a heredoc, a doc string) rather than an actual invocation, this guard cannot distinguish the two -- reword the literal or use \`Read\`/\`Grep\` instead of a shell search."

jq -n --arg reason "$REASON" \
  '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
exit 0
