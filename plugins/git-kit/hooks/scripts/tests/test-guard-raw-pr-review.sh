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
# This suite has been through 3 rounds of the tokenizer's own development:
# round 1 shipped 2 Critical + 3 Major regressions (a security-reviewer +
# hook-reviewer pass caught both); round 2's fix then shipped 3 further Major
# regressions of its own (a second review round caught those). Every prior
# round's cases stay in this suite permanently -- each one is a real,
# previously-shipped bypass, not a hypothetical.
#
# Every e2e helper below captures the guard's exit code explicitly instead of
# relying on `set -e` to propagate it -- an unexpected non-zero exit from the
# guard under test (exactly the class of regression this suite exists to
# catch) must be reported as a named FAIL, not silently abort the whole suite
# before its own PASS/FAIL line prints and before its temp-dir cleanup runs.
#
# Usage: bash test-guard-raw-pr-review.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GUARD="$SCRIPT_DIR/guard-raw-pr-review.sh"
PASS_COUNT=0
FAIL_COUNT=0

# --- Layer 1: unit-level, sourced from the real script -----------------

# Byte-consistent indexing (issue #365, security-review finding C2) -- extract_api_span/
# find_api_spans only behave correctly under this; the real script sets it near its own top, but
# sourcing just the function bodies below (not the whole file) doesn't carry that line along, so
# this suite must set it independently to actually exercise the same behavior the real script has.
export LC_ALL=C

# Source only the two functions and the four regexes out of the real script,
# rather than re-typing them here -- a change to the real script's logic is
# what this suite is meant to catch, not a hand-maintained copy of it.
eval "$(sed -n '/^  extract_api_span() {/,/^  }$/p' "$GUARD")"
eval "$(sed -n '/^    find_api_spans() {/,/^    }$/p' "$GUARD")"
# Portable POSIX sed, not `grep -oP` (hook-reviewer: GNU-only, would silently fail this suite on
# BSD/macOS grep) -- each of these 4 lines in the real script is `VAR='...'` with the value's own
# outermost quotes at the very start and end of the line, so a greedy `.*` between the first and
# last `'` correctly captures the full value, embedded `'"'"'`-style bash quote concatenation
# included (sed matches raw text, not bash quoting semantics, so this doesn't need to understand it).
API_SPAN_PREFIX_RE=$(sed -n "s/^API_SPAN_PREFIX_RE='\(.*\)'\$/\1/p" "$GUARD")
REPLIES_RE=$(sed -n "s/^REPLIES_RE='\(.*\)'\$/\1/p" "$GUARD")
REVIEWS_RE=$(sed -n "s/^REVIEWS_RE='\(.*\)'\$/\1/p" "$GUARD")
GRAPHQL_RE=$(sed -n "s/^GRAPHQL_RE='\(.*\)'\$/\1/p" "$GUARD")

# Checks a span (either the collapsed or raw half of a combined
# "collapsed<0x1E>raw" line) against all three endpoint regexes.
match_span() {
  local span="$1"
  if grep -qE "$REPLIES_RE" <<< "$span"; then echo "replies"; return; fi
  if grep -qE "$REVIEWS_RE" <<< "$span"; then echo "reviews"; return; fi
  if grep -qE "$GRAPHQL_RE" <<< "$span"; then echo "graphql"; return; fi
  echo ""
}

unit_check() {
  local desc="$1" cmd="$2" expect="$3" tool="${4:-Bash}"
  local got="none" combined collapsed raw m
  while IFS= read -r combined; do
    if [ -z "$combined" ]; then continue; fi
    collapsed="${combined%%$'\x1e'*}"
    raw="${combined#*$'\x1e'}"
    m=$(match_span "$collapsed")
    if [ -z "$m" ]; then m=$(match_span "$raw"); fi
    if [ -n "$m" ]; then got="$m"; break; fi
  done < <(find_api_spans "$cmd" "$API_SPAN_PREFIX_RE" "$tool")
  if [ "$got" = "$expect" ]; then
    echo "PASS (unit): $desc"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "FAIL (unit): $desc (expected=$expect got=$got) cmd=[$cmd]"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

# --- Round 1 cases ---

unit_check "365 repro: nested \$(...) w/ embedded pipe" \
  'gh api repos/OWNER/REPO/pulls/N/comments/$(gh api repos/OWNER/REPO/pulls/N/comments --jq '"'"'.[] | select(.user.login == "some-bot") | .id'"'"')/replies -f body="..."' \
  "replies"
unit_check "literal id" \
  'gh api repos/AndreHahm/andres-cc-marketplace/pulls/372/comments/4070166186/replies -F body=@/tmp/x.txt' \
  "replies"
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

# --- Round 2 cases: security-reviewer (C1, C2) + hook-reviewer (independently found C2) ---

unit_check "C1a: endpoint inside \$(echo ...)" \
  'gh api $(echo repos/o/r/pulls/5/reviews) -f event=APPROVE' \
  "reviews"
unit_check "C1b: endpoint inside backtick echo" \
  'gh api `echo repos/o/r/pulls/5/comments/1/replies` -f body=x' \
  "replies"
unit_check "C1c: graphql keyword inside \$(printf)" \
  "gh api \$(printf graphql) -f query='mutation{x}'" \
  "graphql"
unit_check "C2: multibyte em dash before the call" \
  $'echo "done \xe2\x80\x94 next"; gh api repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "reviews"
unit_check "M1(r1): double-quoted nested \$(...) with spaces" \
  'gh api "repos/o/r/pulls/$(gh pr view --json number -q .number)/reviews" -f event=APPROVE' \
  "reviews"
unit_check 'M2a(r1): stray backslash-escaped \\( does not swallow the rest' \
  'gh api -H X-A:\( repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "reviews"
unit_check 'M2b(r1): stray backslash-escaped \\` does not swallow the rest' \
  'gh api -H X-A:\` repos/o/r/pulls/5/reviews' \
  "reviews"

# --- Round 3 cases: a second review round on round 2's own fix ---

unit_check "M1(r2) shape A: quoted ) inside unquoted \$(...)" \
  'gh api -H X:$(echo ")";true) repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "reviews"
unit_check "M1(r2) shape B: quoted stuff inside \$(...) inside outer dquotes" \
  "gh api -H \"X: \$(echo ')\";')\" repos/o/r/pulls/5/reviews -f event=APPROVE" \
  "reviews"
unit_check "M1(r2): single-quote inside \$(...) inside outer dquotes" \
  "gh api \"repos/o/r/pulls/\$(echo 'test')/reviews\"" \
  "reviews"
unit_check "M1(r2) info: literal ( inside dquotes (no \$) must not desync" \
  'gh api user -f body="(see" ; echo repos/o/r/pulls/5/reviews' \
  "none"
unit_check "M1(r2) info: separator inside dquotes at depth 0 still reaches the endpoint" \
  'gh api repos/o/r/pulls/"5/reviews;x"' \
  "reviews"
unit_check "M2(r2): PowerShell desync case now resolves via the per-depth dquote fix" \
  'gh api -H "X: a\" -H "Y: ;b" repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "reviews" "PowerShell"
unit_check "M2(r2): Bash escaped-quote-stays-open, cross-checked against real bash arg-parsing" \
  'gh api -H "a\"b" repos/o/r/pulls/5/reviews' \
  "reviews" "Bash"
unit_check "M2(r2): PowerShell backslash-semicolon is NOT an escape there" \
  'gh api repos/o/r/pulls/5/reviews\; echo unrelated' \
  "reviews" "PowerShell"

# --- Round 4 case: Codex's cross-model-review finding F1 ---
# PowerShell has no backtick command substitution at all -- a backtick there is ALWAYS an escape
# character (like backslash in Bash). Treating every backtick as a Bash-style substitution
# delimiter regardless of shell let a PowerShell caller hide a real separator behind an escaped
# backtick pair, the same bug class M2(r2) already fixed for backslash -- just missed for backtick.

unit_check "F1: PowerShell backtick-escaped \$ and ; -- must still deny" \
  'gh api -H X:`$`; repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "reviews" "PowerShell"
unit_check "F1 control: Bash -- backtick opens real substitution, then a genuine unescaped ; really does separate commands (correctly allowed)" \
  'gh api -H X:`echo hi`; repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "none" "Bash"
unit_check "F1b: PowerShell backtick-escaped backtick itself, endpoint still reachable" \
  'gh api -H X:``` repos/o/r/pulls/5/reviews' \
  "reviews" "PowerShell"
unit_check "F1c: Bash backtick substitution with embedded pipe still works (no regression)" \
  'gh api repos/o/r/pulls/`gh pr view --json number | jq -r .number`/reviews' \
  "reviews" "Bash"

echo ""
echo "=== Layer 2: end-to-end, the real script's actual JSON contract ==="

# Runs the guard as a subprocess and captures BOTH stdout and the real exit
# code explicitly (hook-reviewer, round 2) -- `set -e` must never abort this
# whole suite just because the guard under test exited non-zero, since an
# unexpected non-zero exit is exactly the kind of regression this suite
# exists to catch and report as a named FAIL, not a silent full-suite crash.
e2e_run() {
  local cmd="$1" tool="${2:-Bash}" input rc=0 cmd_file
  # A large $cmd (M3's oversized-payload cases) would blow past the OS's argv size limit if passed
  # to `jq --arg` directly ("Argument list too long") -- write it to a file and use `--rawfile`
  # instead, which reads via the filesystem, not argv.
  cmd_file=$(mktemp)
  printf '%s' "$cmd" > "$cmd_file"
  input=$(jq -n --rawfile cmd "$cmd_file" --arg tool "$tool" '{tool_name: $tool, tool_input: {command: $cmd}}')
  rm -f "$cmd_file"
  E2E_LAST_OUT=$(printf '%s' "$input" | bash "$GUARD" 2>&1) || rc=$?
  E2E_LAST_RC="$rc"
}

e2e_check() {
  local desc="$1" cmd="$2" expect_substr="$3" tool="${4:-Bash}"
  e2e_run "$cmd" "$tool"
  if [ "$E2E_LAST_RC" -ne 0 ]; then
    echo "FAIL (e2e): $desc -- guard exited non-zero (rc=$E2E_LAST_RC): $E2E_LAST_OUT"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    return
  fi
  local out="$E2E_LAST_OUT"
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
e2e_check "C1a via real script -- must deny" \
  'gh api $(echo repos/o/r/pulls/5/reviews) -f event=APPROVE' \
  "deny"
e2e_check "C2 via real script -- must deny (multibyte em dash before the call)" \
  $'echo "done \xe2\x80\x94 next"; gh api repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "deny"
e2e_check "M1(r1) via real script -- must deny" \
  'gh api "repos/o/r/pulls/$(gh pr view --json number -q .number)/reviews" -f event=APPROVE' \
  "deny"
e2e_check 'M2a(r1) via real script -- must deny' \
  'gh api -H X-A:\( repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "deny"
e2e_check "M1(r2) shape A via real script -- must deny" \
  'gh api -H X:$(echo ")";true) repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "deny"
e2e_check "M2(r2) PowerShell via real script -- must deny" \
  'gh api -H "X: a\" -H "Y: ;b" repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "deny" "PowerShell"
e2e_check "F1 via real script -- PowerShell backtick-escape bypass (Codex, cross-model-review) -- must deny" \
  'gh api -H X:`$`; repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "deny" "PowerShell"
m3_big_payload=$(head -c 200000 /dev/zero | tr '\0' 'x')
e2e_check "M3: oversized command containing a gh api prefix -- must deny without hanging" \
  "gh api graphql -f query='${m3_big_payload}'" \
  "deny"
e2e_check "M3 control: oversized command with NO gh api prefix at all -- must allow" \
  "echo '${m3_big_payload}'" \
  "ALLOW"

# Marker-handshake allow path + consumption, and diagnostics logging, both run
# in a temp git dir so this suite never touches the real repo's own marker
# file or diagnostics log. Explicit rc capture, and a RETURN trap for cleanup,
# so a guard crash here is reported as a FAIL rather than aborting the suite
# with the temp dir leaked (hook-reviewer, round 2).
e2e_marker_allow_check() {
  local tmp_git input out
  tmp_git=$(mktemp -d)
  trap 'rm -rf "$tmp_git"' RETURN
  (
    cd "$tmp_git"
    git init -q
    printf 'gh-pr-review %s test-suite\n' "$(date +%s)" > .git/git-kit-marker.txt
    input=$(jq -n '{tool_name: "Bash", tool_input: {command: "gh api repos/o/r/pulls/1/comments/1/replies -f body=x"}}')
    out=$(printf '%s' "$input" | bash "$GUARD") || { echo "FAIL (e2e): marker-handshake allow path + consumption -- guard exited non-zero: $out"; exit 0; }
    if [ -z "$out" ] && [ ! -f .git/git-kit-marker.txt ]; then
      echo "PASS (e2e): marker-handshake allow path + consumption"
    else
      echo "FAIL (e2e): marker-handshake allow path + consumption -- out=[$out] marker_remains=$([ -f .git/git-kit-marker.txt ] && echo yes || echo no)"
    fi
  )
}
marker_result=$(e2e_marker_allow_check)
echo "$marker_result"
if grep -q PASS <<< "$marker_result"; then
  PASS_COUNT=$((PASS_COUNT + 1))
else
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Diagnostics (issue #373/#83): a start+finish pair is logged to the gitignored
# $GIT_DIR/git-kit-guard-diagnostics.log for a normal run, and stdout stays pure,
# parseable JSON throughout -- diagnostics must never leak onto the hook's own
# decision channel.
e2e_diagnostics_check() {
  local tmp_git input out log_lines
  tmp_git=$(mktemp -d)
  trap 'rm -rf "$tmp_git"' RETURN
  (
    cd "$tmp_git"
    git init -q
    input=$(jq -n '{tool_name: "Bash", tool_input: {command: "gh api repos/o/r/pulls/1/reviews"}}')
    out=$(printf '%s' "$input" | bash "$GUARD") || { echo "FAIL (e2e): diagnostics -- guard exited non-zero: $out"; exit 0; }
    if ! jq -e '.hookSpecificOutput.permissionDecision == "deny"' <<< "$out" >/dev/null 2>&1; then
      echo "FAIL (e2e): diagnostics -- stdout was not the expected pure deny JSON: [$out]"
      exit 0
    fi
    log_lines=$(grep -c 'guard=guard-raw-pr-review.sh' .git/git-kit-guard-diagnostics.log 2>/dev/null || echo 0)
    if grep -q 'event=start' .git/git-kit-guard-diagnostics.log 2>/dev/null \
      && grep -q 'event=finish exit=0' .git/git-kit-guard-diagnostics.log 2>/dev/null \
      && [ "$log_lines" -eq 2 ]; then
      echo "PASS (e2e): diagnostics start+finish logged, stdout stayed pure JSON"
    else
      echo "FAIL (e2e): diagnostics -- unexpected log content: $(cat .git/git-kit-guard-diagnostics.log 2>/dev/null || echo '(missing)')"
    fi
  )
}
diag_result=$(e2e_diagnostics_check)
echo "$diag_result"
if grep -q PASS <<< "$diag_result"; then
  PASS_COUNT=$((PASS_COUNT + 1))
else
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

echo ""
echo "=== $PASS_COUNT passed, $FAIL_COUNT failed ==="
[ "$FAIL_COUNT" -eq 0 ]
