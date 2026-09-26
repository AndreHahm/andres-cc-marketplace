#!/bin/bash
# Deterministic regression suite for git-guard-raw-pr-review.sh, run directly
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
# Usage: bash git-test-guard-raw-pr-review.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GUARD="$SCRIPT_DIR/git-guard-raw-pr-review.sh"
PASS_COUNT=0
FAIL_COUNT=0
# Safety net for M4 (round 5): if a future edit reintroduces the span-budget-cap regression this
# suite guards against, an e2e case exercising it should fail fast as a FAIL, not hang the whole
# suite (and CI) indefinitely. GNU `timeout` is expected on this repo's Linux CI; degrades to no
# wrapper (best-effort only) if unavailable, e.g. on a bare macOS host without coreutils.
E2E_TIMEOUT_CMD=()
if command -v timeout >/dev/null 2>&1; then
  E2E_TIMEOUT_CMD=(timeout 20)
fi

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
  local got="none" combined collapsed rest raw force_deny m
  while IFS= read -r combined; do
    if [ -z "$combined" ]; then continue; fi
    collapsed="${combined%%$'\x1e'*}"
    rest="${combined#*$'\x1e'}"
    raw="${rest%%$'\x1e'*}"
    force_deny="${rest#*$'\x1e'}"
    if [ -n "$force_deny" ]; then got="force_deny"; break; fi
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

# --- Round 5 cases: CodeRabbit + Codex, PR #380's own automated review round ---
# ANSI-C quoting (`$'...'`): unlike a plain `'...'` string, `\'` inside it is an escaped quote and
# does not close the string. The old scanner treated every `'` as a closing quote regardless of
# how the quote was opened, so an escaped `\'` inside `$'...'` closed the quote early, letting a
# real `;` right after reopen at depth 0 and truncate the span before the endpoint ever appeared
# in it -- a live, independently-confirmed bypass (CodeRabbit + Codex both found the same defect).
unit_check "G1: Bash ANSI-C \$'...' escaped-quote bypass -- must still deny" \
  "gh api -H \$'x\\'; ' repos/o/r/pulls/5/reviews -f event=APPROVE" \
  "reviews" "Bash"
unit_check "G1 control: plain '...' single-quote still closes on the first quote (no regression)" \
  "gh api -H 'x'; echo repos/o/r/pulls/5/reviews" \
  "none" "Bash"
# Escaped backtick nesting: POSIX -- "within the backquoted style of command substitution,
# backslash shall retain its literal meaning, except when followed by '$', '`', or '\'". The old
# scanner didn't track that escape at all, so it closed `in_backtick` at the first LITERAL
# backtick character even when it was escaped (`\``), absorbing the real closing backtick(s) and
# whatever followed them as ordinary scanned content instead of recognizing the genuinely separate
# command real bash runs after the substitution actually closes.
unit_check "G2: Bash escaped-backtick nested substitution, real ; after -- span must not leak past the real close" \
  'gh api user `echo \`printf x\`` ; echo repos/o/r/pulls/5/reviews' \
  "none" "Bash"
unit_check "G2 control: Bash backtick substitution still closes on a genuine unescaped backtick (no regression)" \
  'gh api -H X:`echo hi` repos/o/r/pulls/5/reviews' \
  "reviews" "Bash"

# --- Round 6 cases: security-reviewer, dispatched on this session's own round-5 fixes ---
# H1 (regression in round 5's OWN fix): the ansi-c detection used a raw textual lookback
# (`${text:i-1:1} = '$'`) instead of scanner state, so it couldn't tell a genuinely fresh,
# unconsumed `$` from one already consumed elsewhere (an escaped `\$`, or the second `$` of `$$`).
# `\$'a\' 'pre;post' ...reviews...` is, in real bash, one literal-`$` argument immediately
# followed by one ORDINARY plain-quoted string (closes normally) -- not ansi-c at all. The buggy
# lookback still marked it ansi-c, so the plain string's own real closing quote was misread as an
# escaped (non-closing) one, staying "in quote" until the NEXT real string's OPENING quote, which
# it then mistook for its own close -- from there a literal `;` genuinely inside that next real
# string read as a live separator, ending the span before the reviews endpoint that followed in
# the same real invocation.
unit_check "H1a: escaped \\\$ before a plain quote must NOT be treated as ansi-c (fixed round-5 regression)" \
  'gh api -H \$'"'"'a\'"'"' '"'"'pre;post-reviews-marker'"'"' repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "reviews" "Bash"
unit_check "H1b: \$\$ (PID) before a plain quote must NOT be treated as ansi-c" \
  'gh api -H $$'"'"'a\'"'"' '"'"'pre;post-reviews-marker'"'"' repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "reviews" "Bash"
unit_check "H1 control: genuine \$'...' ansi-c still detected correctly (no regression from G1)" \
  "gh api -H \$'x\\'; ' repos/o/r/pulls/5/reviews -f event=APPROVE" \
  "reviews" "Bash"

# H2: `${...}` parameter expansion wasn't tracked as a nesting boundary at all -- an unquoted `;`
# inside `${v:-...}` is literal content in real bash (confirmed live), but the old scanner had no
# `{`/`}` handling, so it read that `;` as a real depth-0 separator and stopped the span before an
# endpoint that followed in the same real invocation. Closed by `}`, tracked separately from `)`
# per depth, so a stray `)`/`}` of the wrong type inside either construct can't prematurely close
# the other (`${v:-x)y}` and `$(echo }y)` are both literal content in real bash).
unit_check "H2a: unquoted \${v:-...;...} must not let the ; end the span early" \
  'gh api -H "X:${v:-a;b}" repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "reviews" "Bash"
unit_check "H2b: nested \"...\" inside \${v:-\"...\"} (from within an outer dquote) same fix" \
  'gh api -H "${v:-"a;b"}" repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "reviews" "Bash"
unit_check "H2 control: ordinary \$(...) nesting unaffected by the type-aware )/} change" \
  'gh api repos/o/r/pulls/$(gh pr view --json number | jq -r .number)/reviews' \
  "reviews" "Bash"

# H3: a bare `)` inside `$(...)` isn't always this substitution's own closer in real bash -- a
# `case` pattern's own `x)` terminator is the clearest example (live-verified: `$(case hi in hi)
# echo matched;; esac)` runs as one substitution in real bash). The old scanner decremented depth
# on every bare `)` unconditionally, returning to depth 0 at the case-pattern's own `)` and then
# treating a later real separator as ending the span before an endpoint that, in real bash, was
# still safely inside the still-open substitution. Rather than implement a real case/heredoc/
# comment parser, this scanner denies outright the moment one of those markers appears while
# genuinely unquoted at depth > 0 -- a disclosed false-deny risk in the rare legitimate case one is
# nested this way, never a bypass.
unit_check "H3: case-pattern ) inside \$(...) must force-deny rather than desync depth" \
  'gh api $(case hi in hi) echo unrelated;; esac) repos/o/r/pulls/5/reviews' \
  "force_deny" "Bash"
unit_check "H3 control: ordinary \$(...) with no case/comment/heredoc is unaffected" \
  'gh api repos/o/r/issues/1/comments -f body=$(echo hi)' \
  "none" "Bash"

# H4 (round 6, security-reviewer): four PowerShell-specific constructs this scanner doesn't model
# at all -- a `<# ... #>` block comment, the `--%` stop-parsing token, an `@'...'@`/`@"..."@`
# here-string, and a bare `{...}` script block -- were considered for a fix here, the same
# early-stop risk shape as H1-H3 above. Deliberately deferred, not fixed in this round: this
# environment has no live `pwsh` to verify any of them against, unlike every other fix in this
# file's history. Tracked as a follow-up rather than shipped unverified.

echo ""
echo "=== Layer 2: end-to-end, the real script's actual JSON contract ==="

# Isolate every plain e2e_run/e2e_check case below in one dedicated temp git repo, not this
# script's own cwd. Running against the caller's cwd caused three problems: outside a git repo,
# `git rev-parse --git-dir` fails and the guard exits 0 before any check runs, so every "deny"
# case would falsely report a FAIL; inside the real repo, each case would append start/finish
# lines to the real .git/git-kit-guard-diagnostics.log; and inside the real repo with a marker
# present, a deny case could consume a genuinely pending .git/git-kit-marker.txt, reporting a
# false FAIL while also losing the real marker (CodeRabbit finding, PR #380). One shared repo,
# initialized once here (not per-check, unlike e2e_marker_allow_check/e2e_diagnostics_check
# below, which each need their OWN fresh repo to test marker-consumption/diagnostics-append in
# isolation), removed when the whole suite exits.
E2E_GIT_DIR=$(mktemp -d)
trap 'rm -rf "$E2E_GIT_DIR"' EXIT
git -C "$E2E_GIT_DIR" init -q

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
  # `${E2E_TIMEOUT_CMD[@]+"${E2E_TIMEOUT_CMD[@]}"}`, not a bare `"${E2E_TIMEOUT_CMD[@]}"` -- under
  # this file's own `set -u`, Bash 3.2 (macOS's stock /bin/bash) reports "unbound variable" on an
  # EMPTY array's `[@]` expansion even though the array itself is declared (a known Bash 3.2 bug,
  # fixed in 4.4+); the `+`-guarded form only expands when the array is set/non-empty, on every
  # Bash version (CodeRabbit, PR #380 round 7).
  E2E_LAST_OUT=$(cd "$E2E_GIT_DIR" && printf '%s' "$input" | ${E2E_TIMEOUT_CMD[@]+"${E2E_TIMEOUT_CMD[@]}"} bash "$GUARD" 2>&1) || rc=$?
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
# issue #93 (a flag value like `-f body=graphql` triggers a false-positive deny) is DELIBERATELY NOT
# fixed -- two independent attempts each reopened a worse bug (a bypass) when tried; see
# REPLIES_RE/GRAPHQL_RE/REVIEWS_RE's own comment for the full history. No test asserts the false
# positive itself (that would pin a known bug in place rather than document an accepted gap) -- the
# two controls below just confirm real dangerous endpoints are still denied regardless.
e2e_check "#93 control -- real graphql endpoint immediately after api -- must still deny" \
  'gh api graphql -f query=hello' \
  "deny"
e2e_check "#93 control -- real reviews endpoint after a flag+value pair -- must still deny" \
  'gh api -X POST repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "deny"
e2e_check "M1 (#386 item 5) -- double-quoted api subcommand, real dangerous endpoint -- must deny" \
  'gh "api" repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "deny"
e2e_check "M1 (#386 item 5) -- backslash-escaped api subcommand, real dangerous endpoint -- must deny" \
  'gh \api repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "deny"
e2e_check "M1 -- single-quoted api subcommand, real dangerous endpoint -- must deny" \
  "gh 'api' repos/o/r/pulls/5/reviews -f event=APPROVE" \
  "deny"
e2e_check "M1 -- double-quoted pr review subcommand words -- must deny" \
  'gh "pr" "review" 372 --approve' \
  "deny"
e2e_check "M1 -- double-quoted pr comment subcommand words -- must deny" \
  'gh "pr" "comment" 372 --body hi' \
  "deny"
e2e_check "M1 control -- double-quoted api subcommand, benign endpoint -- must allow" \
  'gh "api" repos/o/r/issues/1/comments -f body=hi' \
  "ALLOW"
# Two review rounds on the #386/M1 fix, each live-verified as a real bypass of the version it found,
# both now fixed by the final presence-based dequoted-fallback design (see API_SPAN_PREFIX_RE's own
# comment, and the fallback check at its point of use, for the full history of attempts 1-3 -- an
# intermediate count-based attempt was also tried and reverted after a third review round; see
# round 3's own cases below).
# Round 1 findings (attempt 1 -- switching the whole scan to dequoted text -- was reverted):
e2e_check "round 1 (security-reviewer) -- quoted api subcommand + quoted semicolon in a header value -- must deny" \
  "gh \"api\" -H 'X-A: a;b' repos/o/r/pulls/5/reviews -f event=APPROVE" \
  "deny"
e2e_check "round 1 (security-reviewer) -- benign plain gh api chained before a quoted dangerous one -- must deny" \
  'gh api user; gh "api" repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "deny"
e2e_check "round 1 variant -- benign plain gh api chained via && before a backslash-escaped dangerous one -- must deny" \
  'gh api user && gh \api graphql -f query=hi' \
  "deny"
# Round 2 findings (attempt 2 -- widening API_SPAN_PREFIX_RE's own alternation -- was reverted):
# unbounded other ways to spell "gh"/"api" via adjacent empty-quote concatenation at arbitrary
# internal positions, none of which a finite enumeration of "quoted forms" could ever cover.
e2e_check "round 2 (security-reviewer) -- empty-quote-prefixed api word -- must deny" \
  "gh ''api repos/o/r/pulls/5/reviews -f event=APPROVE" \
  "deny"
e2e_check "round 2 (security-reviewer) -- api word split by adjacent empty quotes -- must deny" \
  "gh a''pi repos/o/r/pulls/5/reviews -f event=APPROVE" \
  "deny"
e2e_check "round 2 (security-reviewer) -- api word split by a mid-word backslash escape -- must deny" \
  'gh a\pi repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "deny"
e2e_check "round 2 (security-reviewer) -- gh word split by adjacent empty quotes -- must deny" \
  "g''h api repos/o/r/pulls/5/reviews -f event=APPROVE" \
  "deny"
# Round 2 also found attempt 2's OWN trailing-quote widening could consume an unmatched quote and
# desync the scanner (`gh api'' -H 'x;y' ...`) -- not a separate case to fix here, since reverting
# API_SPAN_PREFIX_RE to its original, unwidened form (this design no longer touches that regex at
# all) removes the bug's own root cause entirely; the existing I3-family cases already cover
# adjacent-empty-quote handling in the unmodified scanner.
e2e_check "round 2 control -- hidden-invocation check does not fire on a benign endpoint" \
  'gh "api" repos/o/r/issues/1/comments -f body=hi' \
  "ALLOW"
# Round 3 (security-reviewer): attempt 3's raw match-COUNT comparison (dequoted count > flat count)
# was defeated by "decoy cancellation" -- a decoy prefix match that only exists in COMMAND_FLAT
# because of a stray quote/backslash providing a boundary character elsewhere in the command
# disappears after dequoting, and if its loss exactly offsets a real hidden invocation's gain, the
# counts end up equal and the check never fires. Fixed by dropping the count comparison for a
# presence-based check instead (see API_SPAN_PREFIX_RE's own comment for the current design).
e2e_check "round 3 (security-reviewer) -- decoy cancellation: a backslash-boundary decoy offsets a real hidden invocation -- must deny" \
  'gh a'"'"''"'"'pi repos/o/r/pulls/5/reviews -f event=APPROVE -f body="x\gh api"' \
  "deny"
e2e_check "round 3 -- double decoy, still must deny" \
  'gh a'"'"''"'"'pi repos/o/r/pulls/5/reviews -f event=APPROVE -f a="x\one" -f b="y\two"' \
  "deny"
# Same review round: ANSI-C/locale quoting ($'...'/$"...") hid the subcommand word from BOTH the
# flat regex and a plain quote-strip, since dequoting originally left the `$` in place -- fixed by
# also stripping a leading $'/$" pair in COMMAND_DEQUOTED's own definition (see that variable's
# comment). Covers the `gh pr review`/`gh pr comment` fallback too, since both paths share the same
# COMMAND_DEQUOTED variable.
e2e_check "round 3 -- ANSI-C quoted api subcommand, real dangerous endpoint -- must deny" \
  "gh \$'api' repos/o/r/pulls/5/reviews -f event=APPROVE" \
  "deny"
e2e_check "round 3 -- ANSI-C quoted pr review subcommand words -- must deny" \
  "gh pr \$'review' 372 --approve" \
  "deny"
e2e_check "round 3 -- both gh and pr review ANSI-C quoted -- must deny" \
  "gh \$'pr' \$'review' 372 --approve" \
  "deny"
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
e2e_check "G1 via real script -- Bash ANSI-C \$'...' escaped-quote bypass (CodeRabbit + Codex, round 5) -- must deny" \
  "gh api -H \$'x\\'; ' repos/o/r/pulls/5/reviews -f event=APPROVE" \
  "deny"
# G2's expectation flipped from ALLOW to deny (issue #386, M1's final presence-based fallback fix):
# this command contains a backslash (before the inner backtick), so
# COMMAND_FLAT != COMMAND_DEQUOTED; the dequoted text still has a bare `gh api` prefix (it was never
# hidden here) AND happens to also contain "repos/.../reviews" later, inside the textually-separate
# `echo` command after the real `;`. The M1 fallback check (see API_SPAN_PREFIX_RE's own comment)
# checks the whole dequoted text for a dangerous endpoint ANYWHERE, not attributed to the specific
# `gh api` invocation's own span, so this now denies -- a new, deliberately-accepted false positive
# (a benign call with unrelated dangerous-looking text elsewhere in the same command), the same
# accepted-tradeoff direction this file already established for issue #93 (false-deny over bypass).
# A security-reviewer pass explicitly weighed this cost against closing M1's real bypass and judged
# it acceptable rather than a regression.
e2e_check "G2 via real script -- escaped-backtick nesting (Codex, round 5) -- now denies (issue #386 M1's fallback check fires on the unrelated reviews text after the real ;, an accepted new false positive, not a bypass)" \
  'gh api user `echo \`printf x\`` ; echo repos/o/r/pulls/5/reviews' \
  "deny"
# M4 (round 5, CodeRabbit): a command well under API_SPAN_MAX_LEN bytes can still pack in
# thousands of short `gh api $(`-shaped prefix matches, each independently triggering its own
# worst-case full-remaining-length scan. Left unbounded this is a timeout/fail-open DoS, not just
# a slow test -- live-measured before the api_span_budget_exceeded fix landed: this exact payload
# (13,000 repeats, ~117KB, well under the ORIGINAL 131072-byte length cap in place at the time) took
# long enough to extrapolate to tens of thousands of seconds; after the fix it denies in well under
# a second. Historical payload size preserved as-is below -- API_SPAN_MAX_LEN has since been lowered
# to 32768 (issue #386, M2), so this specific payload (~117KB) is now ALSO caught by the plain
# oversized-length check (line just above the budget-exceeded elif in the real script), not just the
# budget-exceeded path this case was originally written to exercise.
m4_many_prefix_payload=$(printf 'gh api $(%.0s' $(seq 1 13000))
e2e_check "M4: many short gh-api-prefix matches, now also over the (lowered) length cap -- must deny without hanging" \
  "$m4_many_prefix_payload" \
  "deny"
# M4b: a smaller payload, sized to stay UNDER the current (lowered) 32768-byte length cap, so this
# case exercises api_span_budget_exceeded's own cumulative-remaining-length logic specifically --
# not just the simpler raw-length check above. 1,000 repeats of a 9-byte prefix (~9,000 bytes total,
# comfortably under the cap) still drives the SUM of each match's own worst-case remaining-length
# cost well past the 32768 budget (~4.5 * 1000^2 = 4.5M, by this function's own documented
# quadratic-sum accounting), so this keeps the budget-specific path covered going forward.
m4b_many_prefix_payload=$(printf 'gh api $(%.0s' $(seq 1 1000))
e2e_check "M4b: many short gh-api-prefix matches, under the length cap -- must deny without hanging (span-budget cap)" \
  "$m4b_many_prefix_payload" \
  "deny"
e2e_check "H1a via real script -- escaped \\\$ before a plain quote (round 6, security-reviewer) -- must deny" \
  'gh api -H \$'"'"'a\'"'"' '"'"'pre;post-reviews-marker'"'"' repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "deny"
e2e_check "H1b via real script -- \$\$ before a plain quote (round 6) -- must deny" \
  'gh api -H $$'"'"'a\'"'"' '"'"'pre;post-reviews-marker'"'"' repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "deny"
e2e_check "H2 via real script -- \${...} nesting gap (round 6) -- must deny" \
  'gh api -H "X:${v:-a;b}" repos/o/r/pulls/5/reviews -f event=APPROVE' \
  "deny"
e2e_check "H2 control via real script -- \${...} with a ; but no dangerous endpoint -- must allow" \
  'gh api -H "X:${v:-a;b}" repos/o/r/issues/1/comments -f body=hi' \
  "ALLOW"
e2e_check "H3 via real script -- case-pattern ) inside \$(...) (round 6) -- must deny (force-closed)" \
  'gh api $(case hi in hi) echo unrelated;; esac) repos/o/r/pulls/5/reviews' \
  "deny"
# Round 7 (CodeRabbit): force_deny used to deny unconditionally, even when the raw span (now
# extended to end-of-string) never reaches a dangerous endpoint -- this exact shape (a heredoc body
# in an otherwise-benign `gh api` call) was live-verified to wrongly block a routine
# `handling-review-findings` comment-posting call before this fix. force_deny alone must no longer
# deny; only a dangerous endpoint actually present in the extended raw span still does (H3 above).
e2e_check "H3 control (round 7, CodeRabbit) -- case-pattern ) inside \$(...) with NO dangerous endpoint -- must allow" \
  'gh api $(case hi in hi) echo unrelated;; esac) repos/o/r/issues/1/comments' \
  "ALLOW"
# The literal motivating example from CodeRabbit's finding: a routine, benign issue-comment post
# whose heredoc body used to be wrongly force-denied outright, before this round-7 fix.
e2e_check "H5 (round 7, CodeRabbit) -- benign heredoc-body gh api comment post -- must allow" \
  $'gh api repos/o/r/issues/1/comments -f body="$(cat <<\'EOF\'\nhello\nEOF\n)"' \
  "ALLOW"
# The same shape, but the dangerous reviews endpoint follows after the heredoc-containing call --
# must still deny (force_deny's fail-closed property is preserved, not weakened).
e2e_check "H5 control (round 7) -- benign heredoc call followed by a dangerous endpoint -- must deny" \
  $'gh api repos/o/r/issues/1/comments -f body="$(cat <<\'EOF\'\nhello\nEOF\n)" ; gh api repos/o/r/pulls/1/reviews' \
  "deny"

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

# #386 cost-model fix: a marker-authorized call with a large `gh api` argument (well over the
# lowered API_SPAN_MAX_LEN below) must still be ALLOWED, via the new early short-circuit -- not
# denied-without-scanning the way an unauthorized oversized call is. Own isolated repo, same
# pattern as e2e_marker_allow_check above, so this never touches the shared E2E_GIT_DIR's marker.
e2e_marker_shortcircuit_check() {
  local tmp_git payload cmd input out trace
  tmp_git=$(mktemp -d)
  trap 'rm -rf "$tmp_git"' RETURN
  (
    cd "$tmp_git"
    git init -q
    printf 'gh-pr-review %s test-suite\n' "$(date +%s)" > .git/git-kit-marker.txt
    payload=$(head -c 50000 /dev/zero | tr '\0' 'a')
    cmd="gh api repos/o/r/issues/1/comments -f body=${payload}"
    cmd_file=$(mktemp)
    printf '%s' "$cmd" > "$cmd_file"
    input=$(jq -n --rawfile cmd "$cmd_file" '{tool_name: "Bash", tool_input: {command: $cmd}}')
    rm -f "$cmd_file"
    # Uses the same optional E2E_TIMEOUT_CMD wrapper the main e2e_run helper already relies on
    # (defined near this file's own top) -- a bare `timeout 10` here would fail with "command not
    # found" on a platform without GNU coreutils (e.g. a bare macOS host), reporting this case as a
    # FAIL for a portability reason unrelated to the guard's own behavior (Codex fresh-eyes finding,
    # cross-model-review). Degrades to no wrapper (best-effort only) when `timeout` is unavailable.
    # Traced with `bash -x` and asserted against below: empty output + consumed marker alone would
    # still pass even if the short-circuit itself were deleted, since a marker-authorized command
    # that reaches the pre-existing end-of-file `if [ "$allowed" = true ]; then exit 0; fi` is
    # allowed there too, just after paying the full scan cost this test exists to prove is skipped
    # (CodeRabbit finding, PR #404 -- live-verified: reverting the short-circuit locally left this
    # test's old empty-output/marker-consumed assertion passing, while the trace-based one below
    # correctly failed). `COMMAND_FLAT` is only ever assigned once the scan actually starts, well
    # after the short-circuit's own exit point, so its absence from the trace is direct evidence the
    # scan itself was never entered.
    trace="$tmp_git/trace"
    out=$(printf '%s' "$input" | ${E2E_TIMEOUT_CMD[@]+"${E2E_TIMEOUT_CMD[@]}"} bash -x "$GUARD" 2>"$trace") || { echo "FAIL (e2e): marker-authorized oversized call skips the scan (short-circuit) -- guard exited non-zero or timed out: $out"; exit 0; }
    if [ -z "$out" ] && [ ! -f .git/git-kit-marker.txt ] && ! grep -q 'COMMAND_FLAT=' "$trace"; then
      echo "PASS (e2e): marker-authorized oversized call skips the scan (short-circuit)"
    else
      echo "FAIL (e2e): marker-authorized oversized call skips the scan (short-circuit) -- out=[$out] scan_entered=$(grep -q 'COMMAND_FLAT=' "$trace" && echo yes || echo no)"
    fi
  )
}
shortcircuit_result=$(e2e_marker_shortcircuit_check)
echo "$shortcircuit_result"
if grep -q PASS <<< "$shortcircuit_result"; then
  PASS_COUNT=$((PASS_COUNT + 1))
else
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# #386: the lone-CR delimiter-injection check (I2 above) must still deny even when a valid marker
# is present -- the short-circuit's own condition excludes any command containing a `\r` byte
# specifically so this defense-in-depth guarantee survives the new early-exit (see that check's own
# comment in the real script for why). Own isolated repo, same pattern as above.
e2e_marker_cr_still_denies_check() {
  local tmp_git cmd input out
  tmp_git=$(mktemp -d)
  trap 'rm -rf "$tmp_git"' RETURN
  (
    cd "$tmp_git"
    git init -q
    printf 'gh-pr-review %s test-suite\n' "$(date +%s)" > .git/git-kit-marker.txt
    cmd="gh api -H \\$(printf '\r')'x;y' repos/o/r/pulls/5/reviews -f event=APPROVE"
    input=$(jq -n --arg cmd "$cmd" '{tool_name: "Bash", tool_input: {command: $cmd}}')
    out=$(printf '%s' "$input" | bash "$GUARD") || { echo "FAIL (e2e): lone-CR check still denies despite a valid marker -- guard exited non-zero: $out"; exit 0; }
    if grep -q "carriage-return" <<< "$out"; then
      echo "PASS (e2e): lone-CR check still denies despite a valid marker"
    else
      echo "FAIL (e2e): lone-CR check still denies despite a valid marker -- got: $out"
    fi
  )
}
cr_marker_result=$(e2e_marker_cr_still_denies_check)
echo "$cr_marker_result"
if grep -q PASS <<< "$cr_marker_result"; then
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
    log_lines=$(grep -c 'guard=git-guard-raw-pr-review.sh' .git/git-kit-guard-diagnostics.log 2>/dev/null || echo 0)
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

# Round 5 (CodeRabbit): a failed diagnostics-log open (e.g. an unwritable .git dir) must stay
# silent, not leak Bash's own "Permission denied" onto stdout/stderr despite the write's own
# `2>/dev/null` -- an ungrouped `printf ... >> "$DIAG_LOG" 2>/dev/null` still leaks that error
# because the redirect-open failure is reported before the trailing `2>/dev/null` takes effect;
# wrapping the write in a `{ ...; }` group before `2>/dev/null` fixes it. Skipped when running as
# root (root ignores the chmod, so the open wouldn't actually fail and the test proves nothing).
e2e_diag_log_open_failure_check() {
  local tmp_git input out
  if [ "$(id -u)" -eq 0 ]; then
    echo "SKIP (e2e): diagnostics log-open failure stays silent -- running as root, chmod has no effect"
    return
  fi
  tmp_git=$(mktemp -d)
  trap 'chmod 755 "$tmp_git/.git" 2>/dev/null || true; rm -rf "$tmp_git"' RETURN
  (
    cd "$tmp_git"
    git init -q
    chmod 555 .git
    input=$(jq -n '{tool_name: "Bash", tool_input: {command: "gh api repos/o/r/pulls/1/reviews"}}')
    # Stderr is captured to its own file and asserted empty, not just discarded -- a plain
    # `out=$(... | bash "$GUARD")` (no `2>` capture at all) only ever checked stdout, so a
    # regression to the old ungrouped `printf ... >> file 2>/dev/null` form (which leaks Bash's own
    # "Permission denied" straight to the guard's real stderr, before the trailing `2>/dev/null`
    # takes effect) would still report PASS here -- live-verified: reverting the write to that
    # ungrouped form let this exact check pass while real stderr still leaked (CodeRabbit, PR #380
    # round 7).
    err_file=$(mktemp)
    out=$(printf '%s' "$input" | bash "$GUARD" 2>"$err_file") || { echo "FAIL (e2e): diagnostics log-open failure -- guard exited non-zero: $out"; rm -f "$err_file"; exit 0; }
    err=$(cat "$err_file"); rm -f "$err_file"
    if [ -n "$err" ]; then
      echo "FAIL (e2e): diagnostics log-open failure -- guard wrote to stderr: [$err]"
    elif jq -e '.hookSpecificOutput.permissionDecision == "deny"' <<< "$out" >/dev/null 2>&1; then
      echo "PASS (e2e): diagnostics log-open failure stays silent, stdout stayed pure JSON"
    else
      echo "FAIL (e2e): diagnostics log-open failure -- stdout was not the expected pure deny JSON: [$out]"
    fi
  )
}
diag_perm_result=$(e2e_diag_log_open_failure_check)
echo "$diag_perm_result"
if grep -q SKIP <<< "$diag_perm_result"; then
  :
elif grep -q PASS <<< "$diag_perm_result"; then
  PASS_COUNT=$((PASS_COUNT + 1))
else
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Round 7 (Codex): a diagnostics-log path that's a FIFO (or other non-regular-file special file --
# e.g. planted by an attacker before the guard ever runs) must not block the write. Opening it for
# append could hang indefinitely, and combined with this hook's own `onError: "warn"` timeout, that
# turns every guarded operation into a timeout/fail-open bypass. The guard must detect a
# non-regular-file `DIAG_LOG` and skip the write entirely, still completing (and denying) well
# within the test's own bounding `timeout`, with no reader ever attached to the FIFO.
e2e_diag_log_fifo_check() {
  local tmp_git input out
  tmp_git=$(mktemp -d)
  trap 'rm -rf "$tmp_git"' RETURN
  (
    cd "$tmp_git"
    git init -q
    mkfifo .git/git-kit-guard-diagnostics.log
    input=$(jq -n '{tool_name: "Bash", tool_input: {command: "gh api repos/o/r/pulls/1/reviews"}}')
    out=$(printf '%s' "$input" | timeout 5 bash "$GUARD") || { echo "FAIL (e2e): diagnostics FIFO -- guard exited non-zero or timed out: $out"; exit 0; }
    if jq -e '.hookSpecificOutput.permissionDecision == "deny"' <<< "$out" >/dev/null 2>&1; then
      echo "PASS (e2e): diagnostics log FIFO does not block the guard (round 7, Codex)"
    else
      echo "FAIL (e2e): diagnostics FIFO -- stdout was not the expected pure deny JSON: [$out]"
    fi
  )
}
diag_fifo_result=$(e2e_diag_log_fifo_check)
echo "$diag_fifo_result"
if grep -q PASS <<< "$diag_fifo_result"; then
  PASS_COUNT=$((PASS_COUNT + 1))
else
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Round 8 (Codex, P1): a literal ASCII RS (0x1E) byte in the command -- legal inside a quoted shell
# argument -- desyncs extract_api_span/find_api_spans' own 0x1E-delimited return-value protocol,
# letting an attacker-injected delimiter truncate the parsed fields short of a real dangerous
# endpoint that real bash still reaches untouched. Must be rejected outright before any
# span-extraction runs, regardless of what endpoint follows.
e2e_check "I1 (round 8, Codex) -- literal ASCII RS byte before the endpoint -- must deny (delimiter-injection defense)" \
  "gh api 'a$(printf '\x1e')b$(printf '\x1e')c' repos/o/r/pulls/5/reviews -f event=APPROVE" \
  "record-separator"
e2e_check "I1 control (round 8) -- ordinary command with no RS byte -- must allow" \
  'gh api repos/o/r/issues/1/comments -f body=hi' \
  "ALLOW"

# Round 8 (Codex, P2): a diagnostics-log path that's a symlink -- to an existing regular file, or
# dangling -- must never be followed. `[ -f ]`/`[ ! -e ]` alone both dereference a symlink and
# report on its FINAL target, so either shape (symlink-to-regular-file, or a dangling symlink) was
# previously followed, letting the guard repeatedly append diagnostic content to an arbitrary
# external file on every subsequent guarded command.
e2e_diag_log_symlink_check() {
  local tmp_git input target
  tmp_git=$(mktemp -d)
  target=$(mktemp)
  trap 'rm -rf "$tmp_git"; rm -f "$target"' RETURN
  (
    cd "$tmp_git"
    git init -q
    ln -s "$target" .git/git-kit-guard-diagnostics.log
    input=$(jq -n '{tool_name: "Bash", tool_input: {command: "gh api repos/o/r/pulls/1/reviews"}}')
    printf '%s' "$input" | bash "$GUARD" >/dev/null 2>&1
    if [ -s "$target" ]; then
      echo "FAIL (e2e): diagnostics symlink -- guard wrote through the symlink to an external file: $(cat "$target")"
    else
      echo "PASS (e2e): diagnostics log symlink is not followed (round 8, Codex)"
    fi
  )
}
diag_symlink_result=$(e2e_diag_log_symlink_check)
echo "$diag_symlink_result"
if grep -q PASS <<< "$diag_symlink_result"; then
  PASS_COUNT=$((PASS_COUNT + 1))
else
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Round 8 (security-reviewer, on round 8's own fixes): an unconditional blanket strip of every CR
# byte (not just CRLF pairs) changed what the scanner saw relative to real bash whenever a lone CR
# sat next to a backslash or quote -- `\<CR>'x;y'` in real bash embeds a literal CR (backslash
# escapes it) and then opens a real single-quoted string, so the `;` inside never terminates the
# span; after blanket CR-stripping the scanner instead saw `\'x;y'`, read the backslash as escaping
# the quote itself (not opening one), and then treated the bare `;` as a real top-level separator,
# ending the span before a dangerous endpoint real bash still reached. Only a genuine CRLF pair is
# collapsed now; any residual lone CR denies outright instead.
e2e_check "I2 (round 8, security-reviewer) -- lone CR next to a backslash-quote sequence -- must deny (delimiter-injection defense)" \
  "gh api -H \\$(printf '\r')'x;y' repos/o/r/pulls/5/reviews -f event=APPROVE" \
  "carriage-return"
e2e_check "I2 control (round 8) -- ordinary command with no CR byte -- must allow" \
  'gh api repos/o/r/issues/1/comments -f body=hi' \
  "ALLOW"
e2e_check "I2 control 2 (round 8) -- benign CRLF-only multi-line command -- must allow" \
  "gh api repos/o/r/issues/1/comments $(printf '\r')
-f body=hi" \
  "ALLOW"

# Round 8 (security-reviewer): the endpoint regexes match a span's own literal text, but bash
# removes quote marks and escaping backslashes before `gh` ever sees the argument -- `graph''ql`
# and `gr\aphql` both reconstruct to the literal string `graphql` in real bash (live-verified via a
# stub `gh`), evading GRAPHQL_RE's unconditional deny-by-default even though neither the collapsed
# nor raw span contains "graphql" as a contiguous substring for the regex to match.
# Expected substring is now "deny" (generic), not "graphql" (the original span-scan's own specific
# reason label) -- issue #386's own quoted/escaped-invocation fallback check (see API_SPAN_PREFIX_RE's
# own comment) now fires FIRST for these two specific inputs, since both contain a quote/backslash
# byte and dequote to a command containing both a bare `gh api` prefix and the word `graphql`,
# producing its own, differently-worded deny reason -- still correctly denies, just via an earlier
# code path than before. The behavior this test cares about (does the split-word trick still deny)
# is unaffected.
e2e_check "I3 (round 8, security-reviewer) -- graphql split via adjacent empty quotes -- must deny" \
  "gh api graph''ql -f query=hi" \
  "deny"
e2e_check "I3b (round 8) -- graphql split via a mid-word backslash escape -- must deny" \
  'gh api gr\aphql -f query=hi' \
  "deny"
e2e_check "I3c (round 8) -- reviews endpoint split via adjacent empty double-quotes -- must deny" \
  'gh api repos/o/r/pulls/5/re""views -f event=APPROVE' \
  "deny"
e2e_check "I3 control (round 8) -- ordinary quoted/escaped text with no disguised endpoint -- must allow" \
  "gh api repos/o/r/issues/1/comments -f body='it'\\''s fine' -f other=\\x" \
  "ALLOW"

# #386: a NUL byte embedded in the JSON command field, via a valid escaped \u0000 (a raw unescaped
# NUL is not valid JSON in the first place, and is already covered by the existing malformed-JSON
# deny path -- this case is specifically the escaped, well-formed-JSON form). Verified live: jq -r
# decodes \u0000 to a real NUL byte, but bash's own `COMMAND=$(jq -r ...)` command substitution
# silently drops it (a well-documented bash behavior) rather than truncating -- so a dangerous
# endpoint positioned AFTER the NUL in the source text is still reached and matched once the NUL is
# dropped and the surrounding text re-joins. Not a full regression guard against every possible NUL
# placement, but confirms the specific, verified mechanism doesn't silently defeat detection. Own
# isolated repo (bypasses e2e_run/e2e_check, which build the JSON from a plain command string and
# can't express a raw \u0000 escape inside it), same pattern as the marker-focused checks above.
e2e_nul_byte_check() {
  local tmp_git input out
  tmp_git=$(mktemp -d)
  trap 'rm -rf "$tmp_git"' RETURN
  (
    cd "$tmp_git"
    git init -q
    input='{"tool_name":"Bash","tool_input":{"command":"gh api ab\u0000cd repos/o/r/pulls/5/reviews -f event=APPROVE"}}'
    out=$(printf '%s' "$input" | bash "$GUARD") || { echo "FAIL (e2e): NUL byte (#386) -- escaped \\u0000 mid-command, dangerous endpoint follows -- guard exited non-zero: $out"; exit 0; }
    if grep -q "deny" <<< "$out"; then
      echo "PASS (e2e): NUL byte (#386) -- escaped \\u0000 mid-command, dangerous endpoint follows -- must deny"
    else
      echo "FAIL (e2e): NUL byte (#386) -- escaped \\u0000 mid-command, dangerous endpoint follows -- got: $out"
    fi
  )
}
nul_result=$(e2e_nul_byte_check)
echo "$nul_result"
if grep -q PASS <<< "$nul_result"; then
  PASS_COUNT=$((PASS_COUNT + 1))
else
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

echo ""
echo "=== $PASS_COUNT passed, $FAIL_COUNT failed ==="
[ "$FAIL_COUNT" -eq 0 ]
