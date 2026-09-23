#!/bin/bash
# Deterministic regression suite for guard-raw-pr-review.sh, run directly
# against fixtures/known-good output (require-tests-for-behavior-changes.md's
# "Deterministic scripts/code" test category) -- not a blind-agent eval.
#
# Two layers:
#   1. Unit-level: extract_api_span/find_api_spans in isolation, sourced
#      straight from the real script (never a copy-pasted duplicate, so this
#      suite can't silently drift from what actually ships).
#   2. End-to-end: the real script's actual PreToolUse JSON contract, run as
#      a subprocess, covering the marker-handshake allow/consume path too.
#
# Usage: bash test-guard-raw-pr-review.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GUARD="$SCRIPT_DIR/guard-raw-pr-review.sh"
PASS_COUNT=0
FAIL_COUNT=0

# --- Layer 1: unit-level, sourced from the real script -----------------

# Source only the two functions and the four regexes out of the real script,
# rather than re-typing them here -- a change to the real script's logic is
# what this suite is meant to catch, not a hand-maintained copy of it.
eval "$(sed -n '/^  extract_api_span() {/,/^  }$/p' "$GUARD")"
eval "$(sed -n '/^  find_api_spans() {/,/^  }$/p' "$GUARD")"
API_SPAN_PREFIX_RE=$(grep -oP "(?<=^API_SPAN_PREFIX_RE=').*(?=')" "$GUARD")
REPLIES_RE=$(grep -oP "(?<=^REPLIES_RE=').*(?=')" "$GUARD")
REVIEWS_RE=$(grep -oP "(?<=^REVIEWS_RE=').*(?=')" "$GUARD")
GRAPHQL_RE=$(grep -oP "(?<=^GRAPHQL_RE=').*(?=')" "$GUARD")

unit_check() {
  local desc="$1" cmd="$2" expect="$3"
  local got="none"
  while IFS= read -r span; do
    [ -z "$span" ] && continue
    if grep -qE "$REPLIES_RE" <<< "$span"; then got="replies"; break
    elif grep -qE "$REVIEWS_RE" <<< "$span"; then got="reviews"; break
    elif grep -qE "$GRAPHQL_RE" <<< "$span"; then got="graphql"; break
    fi
  done < <(find_api_spans "$cmd" "$API_SPAN_PREFIX_RE")
  if [ "$got" = "$expect" ]; then
    echo "PASS (unit): $desc"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "FAIL (unit): $desc (expected=$expect got=$got) cmd=[$cmd]"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

# Issue #365's exact reported bypass.
unit_check "365 repro: nested \$(...) w/ embedded pipe" \
  'gh api repos/OWNER/REPO/pulls/N/comments/$(gh api repos/OWNER/REPO/pulls/N/comments --jq '"'"'.[] | select(.user.login == "some-bot") | .id'"'"')/replies -f body="..."' \
  "replies"

# Control case #365's own text relied on: literal ID, no nesting, must still deny.
unit_check "literal id" \
  'gh api repos/AndreHahm/andres-cc-marketplace/pulls/372/comments/4070166186/replies -F body=@/tmp/x.txt' \
  "replies"

# The sibling disclosed residual: a quoted value containing a pipe, sitting
# before (not around) the endpoint text.
unit_check "quoted jq value before endpoint" \
  "gh api --jq '.[] | .id' repos/o/r/pulls/5/reviews" \
  "reviews"

unit_check "nested \$(...), simple pipe, reviews endpoint" \
  'gh api repos/o/r/pulls/$(gh pr view --json number | jq -r .number)/reviews' \
  "reviews"

unit_check "backtick-nested substitution with embedded pipe" \
  'gh api repos/o/r/pulls/`gh pr view --json number | jq -r .number`/reviews' \
  "reviews"

unit_check "arithmetic \$((...)) nested" \
  'gh api repos/o/r/pulls/$((1+2))/reviews' \
  "reviews"

unit_check "double-nested \$(...) inside \$(...)" \
  'gh api repos/o/r/pulls/$(echo $(gh pr view --json number | jq -r .number))/reviews' \
  "reviews"

unit_check "graphql via nested \$(...) with pipe" \
  'gh api graphql -f query="$(cat query.gql | tr -d "\n")"' \
  "graphql"

unit_check "graphql, unquoted" \
  'gh api graphql -f query="query { viewer { login } }"' \
  "graphql"

# PR #177's own false-positive regression: unrelated gh api chained with
# unrelated text that happens to contain endpoint-shaped text.
unit_check "false positive: chained benign call + echo containing endpoint text" \
  'gh api user; echo repos/acme/project/pulls/12/reviews' \
  "none"

unit_check "benign call, no guarded endpoint" \
  'gh api repos/o/r/issues/5/comments -f body=hello' \
  "none"

unit_check "chained: benign first call, real second call" \
  'gh api user; gh api repos/o/r/pulls/5/reviews' \
  "reviews"

unit_check "two independent calls via &&, only second guarded" \
  'gh api repos/o/r/issues/1/comments -f body=x && gh api repos/o/r/pulls/2/reviews' \
  "reviews"

unit_check "quoted endpoint (single-quoted)" \
  "gh api 'repos/o/r/pulls/5/comments/9/replies'" \
  "replies"

unit_check "process substitution <(...) standalone, no endpoint" \
  'gh api repos/o/r/issues/5/comments --input <(echo hi)' \
  "none"

unit_check "genuine separate shell word after subst must NOT match" \
  'gh api repos/o/r/pulls/$(cmd) /reviews' \
  "none"

unit_check "literal semicolon still terminates span" \
  'gh api repos/o/r/pulls/5/reviews; echo done' \
  "reviews"

# Malformed-input robustness: must not crash, must not falsely allow a real
# endpoint just because the input is malformed.
unit_check "unmatched closing paren before endpoint" \
  'gh api repos/o/r/pulls)/5/reviews' \
  "reviews"

unit_check "unmatched opening paren, never closes" \
  'gh api repos/o/r/pulls/$(echo unterminated/reviews' \
  "none"

unit_check "unterminated single quote" \
  "gh api repos/o/r/pulls/5/reviews 'unterminated" \
  "reviews"

unit_check "unterminated double quote" \
  'gh api repos/o/r/pulls/5/reviews "unterminated' \
  "reviews"

unit_check "empty gh api call" \
  'gh api' \
  "none"

unit_check "gh api with only whitespace after" \
  'gh api   ' \
  "none"

# --- Layer 2: end-to-end, the real script's actual JSON contract -------

e2e_run() {
  local cmd="$1"
  local input
  input=$(jq -n --arg cmd "$cmd" '{tool_name: "Bash", tool_input: {command: $cmd}}')
  printf '%s' "$input" | bash "$GUARD"
}

e2e_check() {
  local desc="$1" cmd="$2" expect_substr="$3"
  local out
  out=$(e2e_run "$cmd")
  if [ -z "$out" ]; then out="ALLOW (no output)"; fi
  if grep -q "$expect_substr" <<< "$out"; then
    echo "PASS (e2e): $desc"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "FAIL (e2e): $desc -- got: $out"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

e2e_check "365 repro via real script -- must deny" \
  'gh api repos/AndreHahm/andres-cc-marketplace/pulls/372/comments/$(gh api repos/AndreHahm/andres-cc-marketplace/pulls/372/comments --jq '"'"'.[] | select(.user.login == "codex") | .id'"'"')/replies -f body="hi"' \
  "deny"

e2e_check "literal id via real script -- must deny" \
  'gh api repos/AndreHahm/andres-cc-marketplace/pulls/372/comments/4070166186/replies -F body=@/tmp/x.txt' \
  "deny"

e2e_check "benign gh api call via real script -- must allow" \
  'gh api repos/AndreHahm/andres-cc-marketplace/issues/5/comments -f body=hello' \
  "ALLOW"

e2e_check "gh pr review via real script -- must deny (sanity, unrelated to this fix)" \
  'gh pr review 372 --approve' \
  "deny"

e2e_check "gh pr view via real script -- must allow (read-only, unaffected)" \
  'gh pr view 372' \
  "ALLOW"

# Marker-handshake allow path + consumption, run in a temp git dir so this
# suite never touches the real repo's own marker file.
e2e_marker_allow_check() {
  local tmp_git
  tmp_git=$(mktemp -d)
  (
    cd "$tmp_git"
    git init -q
    printf 'gh-pr-review %s test-suite\n' "$(date +%s)" > .git/git-kit-marker.txt
    local input out
    input=$(jq -n '{tool_name: "Bash", tool_input: {command: "gh api repos/o/r/pulls/1/comments/1/replies -f body=x"}}')
    out=$(printf '%s' "$input" | bash "$GUARD")
    if [ -z "$out" ] && [ ! -f .git/git-kit-marker.txt ]; then
      echo "PASS (e2e): marker-handshake allow path + consumption"
    else
      echo "FAIL (e2e): marker-handshake allow path + consumption -- out=[$out] marker_remains=$([ -f .git/git-kit-marker.txt ] && echo yes || echo no)"
    fi
  )
  rm -rf "$tmp_git"
}
marker_result=$(e2e_marker_allow_check)
echo "$marker_result"
if grep -q PASS <<< "$marker_result"; then
  PASS_COUNT=$((PASS_COUNT + 1))
else
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

echo ""
echo "=== $PASS_COUNT passed, $FAIL_COUNT failed ==="
[ "$FAIL_COUNT" -eq 0 ]
