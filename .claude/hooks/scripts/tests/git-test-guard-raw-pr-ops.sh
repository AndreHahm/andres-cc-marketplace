#!/bin/bash
# Deterministic regression suite for git-guard-raw-pr-ops.sh, run directly against fixtures
# (require-tests-for-behavior-changes.md's "Deterministic scripts/code" category) -- not a
# blind-agent eval. It covers the guard's two matchers (`gh pr create`, `gh pr merge`) and the
# repo-override-flag forms found on 2026-10-08, live-verified on gh 2.45.0: `gh -R o/r pr merge`,
# `gh pr -R o/r merge`, `gh --repo=o/r pr create` and the glued `-Ro/r` all run, and the old
# `pr <subcommand>`-must-be-contiguous pattern let every one of them through with no marker check
# -- including the irreversible `gh pr merge`.
#
# Every case runs the real script as a subprocess in its own throwaway git repo, so a marker the
# guard consumes can never be a real pending marker of the repo this suite lives in.
#
# run_guard never runs inside a command substitution: it sets RUN_OUT and RUN_RC directly, so the
# guard's real exit code is checked (a `timeout` kill, rc 124, or a crash with empty output must be
# a FAIL, not an "allow" -- a subshell would silently reset RUN_RC to 0).
#
# Usage: bash git-test-guard-raw-pr-ops.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GUARD="$SCRIPT_DIR/git-guard-raw-pr-ops.sh"
REVIEW_GUARD="$SCRIPT_DIR/git-guard-raw-pr-review.sh"
PASS_COUNT=0
FAIL_COUNT=0
# Shorter than the production hook's 15s timeout (a hook killed by its timeout fails OPEN under
# "onError": "warn"), so a case that would only pass in 15-20s still fails here. Best-effort only:
# the wrapper is skipped when GNU `timeout` is unavailable.
E2E_TIMEOUT_CMD=()
if command -v timeout >/dev/null 2>&1; then
  E2E_TIMEOUT_CMD=(timeout 14)
fi

TMP_GIT=$(mktemp -d)
trap 'rm -rf "$TMP_GIT"' EXIT
git -C "$TMP_GIT" init -q
MARKER_FILE="$TMP_GIT/.git/git-kit-marker.txt"

# run_guard <command> [marker-line]: sets RUN_OUT (stdout+stderr) and RUN_RC (the guard's exit code).
RUN_OUT=""
RUN_RC=0
run_guard() {
  local cmd="$1" marker="${2:-}" input cmd_file
  cmd_file=$(mktemp)
  printf '%s' "$cmd" > "$cmd_file"
  input=$(jq -n --rawfile cmd "$cmd_file" '{tool_name: "Bash", tool_input: {command: $cmd}}')
  rm -f "$cmd_file" "$MARKER_FILE"
  if [ -n "$marker" ]; then
    printf '%s\n' "$marker" > "$MARKER_FILE"
  fi
  RUN_RC=0
  RUN_OUT=$(cd "$TMP_GIT" && printf '%s' "$input" | ${E2E_TIMEOUT_CMD[@]+"${E2E_TIMEOUT_CMD[@]}"} bash "$GUARD" 2>&1) || RUN_RC=$?
}

pass() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "FAIL: $1 -- $2"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

# expect_deny <desc> <command> <guarded-command-name> [marker-line]: the guard must exit 0 and emit a
# deny whose reason names the raw command ("Raw `gh pr merge` is blocked by git-kit's PR-operations
# guard"). Matching the reason text, not just the word "deny", means a crash into the guard's
# fail-closed ERR trap (which emits a different deny reason) cannot pass a case by accident.
expect_deny() {
  local desc="$1" cmd="$2" name="$3" marker="${4:-}" reason
  run_guard "$cmd" "$marker"
  if [ "$RUN_RC" -ne 0 ]; then fail "$desc" "guard exited non-zero (rc=$RUN_RC): $RUN_OUT"; return; fi
  reason=$(jq -r '.hookSpecificOutput.permissionDecisionReason // empty' <<< "$RUN_OUT" 2>/dev/null || true)
  if [ "$(jq -r '.hookSpecificOutput.permissionDecision // empty' <<< "$RUN_OUT" 2>/dev/null || true)" = "deny" ] \
    && grep -qF "Raw \`$name\` is blocked by git-kit's PR-operations guard" <<< "$reason"; then
    pass "$desc"
  else
    fail "$desc" "expected a deny naming \`$name\`, got: ${RUN_OUT:-ALLOW (no output)}"
  fi
}

# expect_allow <desc> <command> [marker-line]: exit 0 and no output at all. With a marker line, the
# marker must also have been consumed (a matched-and-authorized call), which a non-matching pattern
# would not do.
expect_allow() {
  local desc="$1" cmd="$2" marker="${3:-}"
  run_guard "$cmd" "$marker"
  if [ "$RUN_RC" -ne 0 ]; then fail "$desc" "guard exited non-zero (rc=$RUN_RC): $RUN_OUT"; return; fi
  if [ -n "$RUN_OUT" ]; then fail "$desc" "expected allow, got: $RUN_OUT"; return; fi
  if [ -n "$marker" ] && [ -f "$MARKER_FILE" ]; then
    fail "$desc" "allowed, but the marker was not consumed (the guard did not recognize the command)"
    return
  fi
  pass "$desc"
}

NOW=$(date +%s)

# --- denies -------------------------------------------------------------------------------------
# The first two are controls (already denied before the fix); every other deny case below was an
# ALLOW under the old contiguous `pr <subcommand>` pattern.
expect_deny "control: plain gh pr merge" 'gh pr merge 5 --rebase' 'gh pr merge'
expect_deny "control: plain gh pr create" 'gh pr create --title t --body b' 'gh pr create'
expect_deny "root -R before pr merge" 'gh -R o/r pr merge 5 --rebase' 'gh pr merge'
expect_deny "pr -R before merge" 'gh pr -R o/r merge 5 --rebase' 'gh pr merge'
expect_deny "root --repo before pr merge" 'gh --repo o/r pr merge 5' 'gh pr merge'
expect_deny "pr --repo=o/r before merge" 'gh pr --repo=o/r merge 5' 'gh pr merge'
expect_deny "glued -Ro/r before merge" 'gh pr -Ro/r merge 5' 'gh pr merge'
expect_deny "root -R before pr create" 'gh -R o/r pr create --fill' 'gh pr create'
expect_deny "pr --repo before create" 'gh pr --repo o/r create --fill' 'gh pr create'
expect_deny "flags at both positions before merge" 'gh -R o/r pr -R p/q merge 5' 'gh pr merge'
expect_deny "gh.exe with root -R before merge" 'gh.exe -R o/r pr merge 5' 'gh pr merge'
expect_deny "double-quoted repo value before merge" 'gh -R "o/r" pr merge 5' 'gh pr merge'
expect_deny "chained after another command" 'echo hi && gh -R o/r pr merge 5 --squash' 'gh pr merge'
expect_deny "command substitution" 'echo $(gh pr -R o/r merge 5)' 'gh pr merge'
# Non-repo flags valid on the final command also sit before the subcommand words (cobra; live-verified:
# `gh --json=number pr view 1`, `gh pr --squash=true merge --help`), as do flags with a separate value.
expect_deny "root --squash=true before pr merge" 'gh --squash=true pr merge 5' 'gh pr merge'
expect_deny "pr --squash=true before merge" 'gh pr --squash=true merge 5' 'gh pr merge'
expect_deny "root --admin=true before pr merge" 'gh --admin=true pr merge 5' 'gh pr merge'
expect_deny "pr -d=true before merge" 'gh pr -d=true merge 5' 'gh pr merge'
expect_deny "pr -d with a separate value before merge" 'gh pr -d true merge 5' 'gh pr merge'
expect_deny "pr bare --auto before merge" 'gh pr --auto merge 5' 'gh pr merge'
expect_deny "pr glued -bX before create" 'gh pr -bx create' 'gh pr create'
expect_deny "pr --title=t before create" 'gh pr --title=t create' 'gh pr create'
expect_deny "root --fill=true before pr create" 'gh --fill=true pr create' 'gh pr create'
expect_deny "mixed repo and other flags both positions" 'gh -R o/r --admin=true pr --squash=true -d merge 5' 'gh pr merge'
# `gh pr new` is a built-in alias of `gh pr create` (live-verified), so it is the same raw invocation.
expect_deny "gh pr new alias" 'gh pr new --fill' 'gh pr create'
expect_deny "gh pr new alias with repo flag" 'gh -R o/r pr new --fill' 'gh pr create'
expect_deny "gh pr new alias with another flag" 'gh pr --title=t new' 'gh pr create'
# A quoted flag value containing whitespace is ONE argument to bash, so it must not break the flag group
# (security re-audit b3r-2; each of these was an ALLOW before the quote-aware value alternatives).
expect_deny "double-quoted spaced value before merge" 'gh pr --subject "Release v2" merge 5' 'gh pr merge'
expect_deny "single-quoted spaced value before create" "gh pr --title 'fix bug' create" 'gh pr create'
expect_deny "quoted spaced value then repo flag before merge" 'gh pr --body "a b c" -R o/r merge 5' 'gh pr merge'
expect_deny "quoted spaced value at the root before pr merge" 'gh --subject "Release v2" pr merge 5' 'gh pr merge'
# b3f-2 (security recheck): a flag and its value are shell WORDS, so an EMBEDDED quote with several spaces
# (`--subject="ship it now"`) or adjacent quoted segments must not break the flag group. The merge guard
# is the highest-impact path and has no dequote fallback, so these were plain ALLOWs before.
expect_deny "embedded double-quoted 3-word value before merge" 'gh pr --subject="ship it now" merge 5' 'gh pr merge'
expect_deny "embedded single-quoted 3-word value before create" "gh pr --title='ship it now' create" 'gh pr create'
expect_deny "embedded quoted value on a root flag before pr merge" 'gh --body="x y z" pr merge 5' 'gh pr merge'
expect_deny "quote glued to the flag letter before merge" 'gh pr -b"two words here" merge 5' 'gh pr merge'
expect_deny "adjacent double- and single-quoted segments as one value" "gh pr --body \"a b\"'c d' merge 5" 'gh pr merge'
# Disclosed over-match (b3r-4): a flag whose VALUE equals a guarded word can be read as the subcommand
# even though gh runs it as `pr list`. Fail-safe direction; pinned here so it cannot change silently.
expect_deny "disclosed over-match: flag value 'merge' before pr list" 'gh pr --search merge list' 'gh pr merge'

# --- allows: not the guarded subcommands --------------------------------------------------------
expect_allow "gh pr view with -R" 'gh pr view 5 -R o/r --json number'
expect_allow "root -R before pr view" 'gh -R o/r pr view 5 --json number'
expect_allow "gh pr list searching the word merge" 'gh pr list -R o/r --search merge'
expect_allow "gh pr checks" 'gh pr checks 5 --required'
expect_allow "gh issue create is another command" 'gh -R o/r issue create --title t'
expect_allow "unrelated command" 'git status'
expect_allow "other flags before gh pr view" 'gh --json=number pr view 1 -R o/r'
expect_allow "other flags after the group word on pr view" 'gh pr --web=false view 1'
expect_allow "gh pr list searching the word new" 'gh pr list --search new'
expect_allow "gh pr view naming a branch called merge" 'gh pr view merge'
expect_allow "newer is not the new alias" 'gh pr newer-thing'
expect_allow "gh issue merge is not a pr command" 'gh -R o/r issue merge 5'
expect_allow "embedded quoted 3-word value before pr view" 'gh pr --title="ship it now" view 5'
expect_allow "quoted spaced value before pr view" 'gh pr --title "fix bug" view 5'
expect_allow "quoted spaced value before pr list" "gh pr --search 'release v2' list"

# --- marker handshake: a fresh matching marker authorizes the flagged form, and is consumed -----
expect_allow "fresh gh-pr-merge marker authorizes a flagged merge (marker consumed)" \
  'gh pr -R o/r merge 5 --rebase' "gh-pr-merge $NOW test-suite"
expect_allow "fresh gh-pr-create marker authorizes a flagged create (marker consumed)" \
  'gh -R o/r pr create --fill' "gh-pr-create $NOW test-suite"
# A marker of the wrong guard type must not authorize the other command, and a stale one must not
# authorize either.
expect_deny "wrong-type marker does not authorize a flagged merge" \
  'gh -R o/r pr merge 5' 'gh pr merge' "gh-pr-create $NOW test-suite"
expect_deny "stale marker does not authorize a flagged merge" \
  'gh -R o/r pr merge 5' 'gh pr merge' "gh-pr-merge $((NOW - 600)) test-suite"

# --- stress: a very long run of flags must neither hang the matcher nor change the verdict ------
# A timeout kill (rc 124) is reported by run_guard's rc check as a FAIL for both cases below.
long_flags=$(printf ' -R o/r%.0s' $(seq 1 1500))
expect_deny "1500 repeated flags then pr merge" "gh${long_flags} pr merge 5" 'gh pr merge'
expect_allow "1500 repeated flags then pr view, no hang" "gh pr${long_flags} view 5"
# Other flag shapes, and the adversarial near-miss that never reaches a `pr` word at all (the shape a
# backtracking matcher would be slowest on): thousands of flag-and-value tokens, no guarded command.
mixed_flags=$(printf ' --x=1 -y z -w%.0s' $(seq 1 1500))
expect_deny "1500 mixed flag/value groups then pr merge" "gh pr${mixed_flags} merge 5" 'gh pr merge'
expect_allow "1500 mixed flag/value groups then pr view, no hang" "gh pr${mixed_flags} view 5"
no_pr_flags=$(printf ' -R o/r --x=1 -y z%.0s' $(seq 1 3000))
expect_allow "3000 flag groups with no pr word at all, no hang" "gh${no_pr_flags} issue list"
huge_flags=$(printf ' -R o/r%.0s' $(seq 1 20000))
expect_allow "roughly 140KB of repeated flags with no guarded command, no hang" "gh pr${huge_flags} view 5"

# --- drift: GH_FLAGS lives in two guards, and a third copy sits inside API_SPAN_PREFIX_RE -----------
# The guards are standalone scripts with no shared sourced library, so a fix applied to one copy of
# the pattern would silently leave the others behind. Extract the assignments straight from the real
# scripts and require them byte-identical, and require the same group to appear literally inside the
# review guard's API_SPAN_PREFIX_RE (written out there, not spliced, because the review suite's unit
# tests extract that line verbatim).
flags_ops=$(sed -n "s/^GH_FLAGS='\(.*\)'\$/\1/p" "$GUARD")
flags_review=$(sed -n "s/^GH_FLAGS='\(.*\)'\$/\1/p" "$REVIEW_GUARD")
api_prefix=$(sed -n "s/^API_SPAN_PREFIX_RE='\(.*\)'\$/\1/p" "$REVIEW_GUARD")
if [ -z "$flags_ops" ] || [ -z "$flags_review" ]; then
  fail "GH_FLAGS drift check" "could not extract the pattern from both guards (ops=[${flags_ops:-}] review=[${flags_review:-}])"
elif [ "$flags_ops" = "$flags_review" ]; then
  pass "GH_FLAGS is identical in git-guard-raw-pr-ops.sh and git-guard-raw-pr-review.sh"
else
  fail "GH_FLAGS drift check" "ops=[$flags_ops] review=[$flags_review]"
fi
if [ -n "$flags_review" ] && grep -qF -- "$flags_review" <<< "$api_prefix"; then
  pass "API_SPAN_PREFIX_RE in git-guard-raw-pr-review.sh contains the same flag group"
else
  fail "API_SPAN_PREFIX_RE drift check" "flag group [${flags_review:-}] not found inside [${api_prefix:-}]"
fi

echo ""
echo "=== $PASS_COUNT passed, $FAIL_COUNT failed ==="
[ "$FAIL_COUNT" -eq 0 ]
