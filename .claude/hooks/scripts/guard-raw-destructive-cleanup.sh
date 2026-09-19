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

# Normalized copy of $COMMAND for the span-based matching below (BRANCH_SPANS,
# WORKTREE_REMOVE_SPANS): a backslash-continued command (`git worktree remove
# ./wt \` + newline + `  --force`) is one logical command to bash but
# multiple records to a line-oriented `grep`, splitting the span extraction
# across records and losing a flag that lands on a later "line" -- live-
# verified as a real bypass for both span checks below. Fold `\` + newline
# into nothing (matching bash's own line-continuation semantics: it splices
# with no inserted character) and convert any remaining bare newline (a
# genuinely separate command, e.g. from a heredoc or pasted multi-line
# input) to `;`, a real command separator the span extraction already
# terminates on. Pure bash parameter expansion, not sed/perl -- no new
# dependency on top of the jq/git/grep this file already requires. See
# issue #116.
# Three refinements, all live-verified as necessary, not theoretical:
# (1) Strip `\r` unconditionally, first, before either substitution below --
#     a CRLF line ending otherwise leaves the `\r` sitting between the `\`
#     and the `\n`, so the backslash+LF pattern below never matches it, and
#     the bare-LF-to-`;` conversion then inserts a terminator in the middle
#     of what should have been one continued span, severing a trailing
#     force flag from its own invocation (a CRLF variant of the exact
#     bypass this fix exists to close).
# (2) The line-continuation splice is shell-specific, not a single rule
#     applied to both: Bash's is backslash+newline; PowerShell's own
#     continuation character is the backtick, not a backslash -- a
#     PowerShell command ending in a literal trailing backslash is an
#     ordinary Windows path (e.g. `cd C:\repo\`), not a continuation --
#     splicing a character a given shell treats as a literal, not a
#     continuation, misrepresents that shell's own statement boundaries
#     (the two lines really are separate statements to it), even though
#     GIT_PREFIX's own boundary class would still recognize a `git`
#     invocation immediately after the spliced-away backslash either way.
#     Each shell only gets its own continuation
#     character spliced; a bare trailing backslash in a PowerShell command,
#     or a bare trailing backtick in a Bash command, is just a literal
#     character in that shell's own syntax, correctly left untouched and
#     therefore correctly landing on the "bare newline -> `;`" branch
#     below as a real separator, not a continuation.
# (3) BRANCH_SPANS' own match logic (below) evaluates each extracted span
#     independently, in a loop, never against the whole multi-span blob at
#     once -- a chained pair of unrelated `git branch` invocations
#     otherwise cross-contaminates: a delete flag from one plus a
#     protected name from the other reads as a match neither invocation
#     alone is. WORKTREE_REMOVE_SPANS' own check further below now ALSO
#     requires per-span isolation (revised from an earlier version of this
#     comment, which said it didn't) -- not for the cross-contamination
#     reason BRANCH_SPANS has, but because its own `--`-terminator
#     truncation (issue #177 round 2, Fix C) operates on one span's text at
#     a time: truncating a concatenated multi-span blob at the first
#     standalone `--` would silently discard every later span's own content
#     entirely, not just that one span's own tail past its terminator.
COMMAND_FLAT="${COMMAND//$'\r'/}"
if [ "$TOOL_NAME" = "Bash" ]; then
  COMMAND_FLAT="${COMMAND_FLAT//$'\\\n'/}"
elif [ "$TOOL_NAME" = "PowerShell" ]; then
  COMMAND_FLAT="${COMMAND_FLAT//$'`\n'/}"
fi
COMMAND_FLAT="${COMMAND_FLAT//$'\n'/;}"
# De-fang redirection operators that contain a `;`/`&`/`|` byte the span
# terminator class below (`[^;&|]`) would otherwise mistake for a real
# command separator, before span extraction below -- issue #120 (partial
# fix; the original quoted-`;`/`&`/`|` vector that issue was filed for
# remains a documented residual, see BRANCH_SPANS'/WORKTREE_REMOVE_SPANS'
# own notes further down). Full, explicit coverage table of every bash/
# PowerShell redirection operator containing one of those three bytes --
# stated as a table so future completeness is checkable rather than
# re-derived from scratch (this table itself was only completed after a
# security-review round found `>|` missing from an earlier version that
# claimed, incorrectly, to have proven the operator SET complete):
#   &>    redirect stdout+stderr             -> de-fanged below
#   &>>   append stdout+stderr               -> de-fanged below (contains `&>`)
#   >&    fd-duplication (`2>&1`, etc.)      -> de-fanged below
#   <&    fd-duplication (`0<&1`, etc.)      -> de-fanged below
#   >|    noclobber-override redirect        -> de-fanged below
#   |&    pipe stderr+stdout (`cmd1 |& cmd2`) -> deliberately NOT touched --
#         this is a genuine command separator (shorthand for `2>&1 |`), and
#         the leading `|` already correctly terminates the span on its own;
#         no separate handling needed.
# Live-verified as real bypasses before each was added: `git worktree
# remove ./wt 2>&1 --force`/`git branch main 2>&1 -D` (truncated at the `&`
# in `2>&1`), `git worktree remove ./wt 0<&1 --force` (the `<&` form), and
# `git worktree remove ./wt >|/dev/null --force`/`git branch main
# >|/dev/null -D` (the `>|` form, found in a later review round -- `|` is a
# span terminator on its own, distinct from the `&`-based operators above).
# Plain literal substring replacement (`&>` -> ` >`, `>&` -> `> `, `<&` ->
# `< `, `>|` -> `> `), not a digit-matching pattern: an earlier attempt used
# a bash glob `[0-9]*>&[0-9]*`, which in glob syntax means "one digit then
# ANY characters" (not "zero-or-more digits", unlike regex) and consumed
# far more of the string than intended -- reverted in favor of this
# simpler, digit-agnostic form, which only ever touches the operator itself
# and leaves any surrounding fd-number digits untouched.
# Soundness is per-operator, not a claim that this set is exhaustive (see
# the table above for what "exhaustive" actually required): in valid,
# unescaped bash, `&` immediately followed by `>` -- or `<`/`>` immediately
# followed by `&` -- can only ever be one of the `&`-based operators, never
# a real separator, since a bare `&` (backgrounding) followed by a redirect
# must have whitespace between them (`cmd & >file`, not `cmd &>file`), and
# a bare `<`/`>` redirect requires a word target, not an `&`. Likewise `>`
# immediately followed by `|` can only ever be the noclobber-override
# redirect, never `>` followed by a structurally-valid standalone pipe.
# Residual, not a bypass: a backslash-escaped or quoted `>` immediately
# before a real `|` (e.g. `git worktree remove ./a\>|rm -f x`, where the
# `|` is a genuine separator) still gets de-fanged by this substitution --
# but only ever widens the resulting span, so the fail-safe direction below
# still holds; it can never hide a flag that would otherwise have been
# caught. Each substitution therefore only ever fires on a byte sequence
# that either was never a command separator to begin with, or -- in this
# one escaped/quoted edge case -- fires on a real separator but only in the
# harmless, span-widening direction. It can only make a span larger
# (fail-safe), never smaller. Deliberately leaves a standalone `&` or `|`
# (backgrounding / piping) alone -- none of these patterns matches either
# with no adjacent `<`/`>`, so each still correctly terminates the span as
# a real separator, not a continuation. Covers PowerShell's own redirection
# set too (`2>&1`, `*>&1`, `n>&1`); PowerShell has no `<&` or `>|` form
# (per PowerShell's documented redirection operators -- not independently
# executed/confirmed in this environment).
COMMAND_FLAT="${COMMAND_FLAT//&>/ >}"
COMMAND_FLAT="${COMMAND_FLAT//>&/> }"
COMMAND_FLAT="${COMMAND_FLAT//<&/< }"
COMMAND_FLAT="${COMMAND_FLAT//>|/> }"

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
    # `if ! rm -f ...; then ...` -- not the earlier `rm -f "$MARKER" || true` --
    # so a genuinely failed deletion (e.g. .git becomes read-only/permission-
    # restricted after the marker was written, the marker file itself still
    # readable) withholds authorization instead of trusting a marker we
    # couldn't actually consume. Live-verified as a real bug before this fix:
    # the old `|| true` form let `allowed` stay `true` from the check above
    # while the marker stayed on disk unconsumed, so a later matching command
    # within the remaining TTL could also be authorized by the same
    # once-intended marker -- found independently by both Devin and Codex on
    # PR #177. An `if` construct is itself exempt from `set -e`/the ERR trap
    # (same exemption this file's own `[ -n ... ]` wrapping elsewhere relies
    # on), so this closes the gap without reopening the session-wide-lockout
    # risk the original `|| true` existed to prevent -- a persistent .git
    # permission problem now just denies cleanly via this normal "no valid
    # marker" path, not a crash through fail_closed_deny. Residual, narrower
    # than before: if the underlying failure is transient and a LATER,
    # unrelated call's own `rm -f` succeeds in deleting this same leftover
    # marker, that later call could still be authorized by it (bounded by the
    # original 60s TTL) -- not fully closed here, since doing so needs a
    # tombstone mechanism disproportionate to this edge case's likelihood.
    if ! rm -f "$MARKER"; then
      allowed=false
    fi
  fi
fi

MATCH=false

# `git branch -D <name>` (or the equivalent `-d -f`/`-f -d`/`-df`/`-fd`/
# `--delete --force` spellings), only when <name> is one of the protected
# patterns -- rewritten from a single positional regex (flags, then the
# name, in that exact order) to a span-bounded check with two independent
# conditions, mirroring WORKTREE_REMOVE_SPANS/FORCE_FLAG_RE below. The old
# positional form missed three confirmed, live-verified bypasses: multiple
# branch names where the protected one isn't first (`git branch -D feature
# main` deletes main -- git accepts multiple names to `-D`), options placed
# after the branch name (`git branch main -D`, since `git branch`'s own
# argument parser permutes non-option arguments), and delete/force spelling
# combinations the old enumerated alternation didn't cover (`--delete -f`,
# `-d --force`, bundled `-Df`/`-fD`, and abbreviated long options
# `--d`/`--forc` -- git's own parse-options accepts any unambiguous
# prefix -- all confirmed as real, working git syntax). See issue #116.
# `grep -oE` emits one line per matched `git branch` invocation when
# $COMMAND_FLAT contains more than one (e.g. `git branch -d a && git branch
# -f main origin/main`, two unrelated, individually-benign commands) --
# each span below is matched independently in its own loop iteration, never
# against the concatenated multi-span blob, so a delete flag from one
# invocation can never combine with a protected name from a different one
# to produce a false match neither invocation alone is.
# Residual, same as WORKTREE_REMOVE_SPANS' own note further below (issue
# #120): the span terminator class (`[^;&|]`) can't distinguish a real
# shell separator from the same byte inside two related cases the
# `COMMAND_FLAT` de-fang step above doesn't reach: (1) a quoted branch name
# literally containing `;`/`&`/`|` placed before the delete flag, and (2)
# an unquoted nested construct -- `$(...)`, backticks, `$((...))`,
# `<(...)` -- whose own body contains one of these bytes (e.g. `git branch
# $(echo main) -D`), which the span extraction has no way to treat as a
# single, non-terminating unit. Both need real shell tokenization to close
# properly, not a character-class cut -- out of scope for this fix, tracked
# in #120. (The enumerated redirection-operator set -- `&>`/`&>>`/`>&`/
# `<&`/`>|` -- IS closed by the `COMMAND_FLAT` de-fang step above, before
# this span is ever extracted; see that step's own comment for the full
# operator table and why it's a per-operator soundness claim, not a claim
# that every possible redirection-adjacent bypass is closed.)
BRANCH_SPANS=$(echo "$COMMAND_FLAT" | grep -oE "${GIT_PREFIX}branch[^;&|]*" || true)
# `-D` (or any short-option cluster containing uppercase `D`, e.g. `-Df`/
# `-fD`) is git branch's own force-delete flag -- no other git-branch short
# flag uses uppercase `D`, so any token containing it in this span is a
# force-delete, regardless of what else is bundled into the same token.
# Trailing boundary widened to the same negated-identifier class as
# GIT_PREFIX/FORCE_FLAG_RE -- not `([[:space:]]|$)` as this line originally
# read. That narrower trailing class missed the same wrapper shapes issue
# #85 already found and fixed for the sibling FORCE_FLAG_RE below: `bash -c
# "git branch main -D"` (trailing quote after `-D`), `$(git branch -d main
# -f)` (trailing paren after `-f`), and `(cd /repo && git branch main -D)`
# (same) all confirmed live to bypass the narrower class.
# Leading boundary is `(^|[[:space:]])` plus an optional quote/backslash,
# not the fully negated-identifier class GIT_PREFIX/FORCE_FLAG_RE use --
# that wider class was tried and reverted after live-testing found it
# created real false-positive denials on ordinary read-only `git branch`
# invocations: `--sort=-committerdate` (the `=` before the dash admits
# `-committerdate` as a bogus flag cluster containing `d`) and
# `--format='...-DEV'` (the `'` before the dash admits `-DEV` as a bogus
# cluster containing `D`). The optional `["'\]?` tolerance (same shape
# BRANCH_NAME_RE below already uses) restores coverage for a deliberately
# quoted or escaped flag (`git branch "-D" main`, `git branch '-D' main`,
# `git branch \-D main`) without reopening either false positive -- in
# both, the `=`/`'` sits immediately after another non-whitespace
# character, not after whitespace, so the `(^|[[:space:]])` anchor before
# the optional quote class still correctly excludes them. All three of
# this issue's own confirmed bypasses are trailing-side only and remain
# covered regardless, since the flag is always whitespace-preceded in each
# -- found via three consecutive security-reviewer passes on this same
# fix, after three earlier rounds each missed one facet of this asymmetry
# in turn.
BRANCH_D_RE='(^|[[:space:]])["'"'"'\\]?-[A-Za-z]*D[A-Za-z]*([^[:alnum:]_.-]|$)'
# `-d`/`--delete` (non-forced delete) only counts as a deletion path when
# paired with BRANCH_FORCE_RE below -- git refuses a plain `-d` on an
# unmerged branch, which main/master/develop/release/* normally are, so
# `-d` alone isn't the same guaranteed-destructive action `-D`/`-d -f` is.
# `--d[a-z]*`/`--forc[a-z]*`, not the exact literal `--delete`/`--force` --
# git's own parse-options accepts any unambiguous prefix, and the minimum
# accepted length differs per option: `--delete` is git branch's only long
# option starting with "d" at all, so even the bare 1-letter `--d` is
# already unambiguous and git-accepted (live-verified: `git branch --d -f
# main` force-deletes main); `--force` needs 4 letters (`--forc`) before
# it's unambiguous, since `--format` shares the same first 3.
BRANCH_LOWER_D_RE='(^|[[:space:]])["'"'"'\\]?(-[A-Za-z]*d[A-Za-z]*|--d[a-z]*)([^[:alnum:]_.-]|$)'
BRANCH_FORCE_RE='(^|[[:space:]])["'"'"'\\]?(-[A-Za-z]*f[A-Za-z]*|--forc[a-z]*)([^[:alnum:]_.-]|$)'
# Independent of flag position -- a protected name is a match wherever it
# appears in the span, not just immediately after the delete flag. `<name>`
# may optionally be quoted -- `git-cleanup/SKILL.md` itself instructs
# quoting the branch variable, so an unquoted-only match would miss the
# exact form that skill is told to write.
# Split into two patterns, not one combined alternation, because the correct
# trailing boundary differs per branch of the match: `main`/`master`/`develop`
# are EXACT protected names, so `/` must NOT count as a valid trailing
# boundary after them -- the single negated-identifier class
# `[^[:alnum:]_.-]` used everywhere else in this file admits `/` (it's not
# alnum/underscore/dot/hyphen), which let `main/topic` (a genuinely different,
# unprotected branch that merely shares a prefix) match as "main" and get
# incorrectly denied -- live-verified, found by Devin's review of PR #177.
# `release/*`, in contrast, NEEDS `/` to keep matching -- its own body already
# captures everything through the trailing boundary via
# `release/[^[:space:]"']*`, so its half of the check is unchanged.
BRANCH_NAME_RE='(^|[[:space:]])["'"'"']?(main|master|develop)["'"'"']?([^[:alnum:]_./-]|$)'
BRANCH_RELEASE_RE='(^|[[:space:]])["'"'"']?release/[^[:space:]"'"'"']*["'"'"']?([^[:alnum:]_.-]|$)'
if [ -n "$BRANCH_SPANS" ]; then
  while IFS= read -r branch_span; do
    # `if [ -z ... ]; then continue; fi`, not `[ -z ... ] && continue` --
    # the latter's failing `[` sits inside a `&&` list, which is exempt from
    # both `set -e` and the ERR trap; harmless today (an empty span just
    # isn't a match), but fragile in a script whose ERR trap denies
    # unconditionally -- an `if` doesn't depend on that exemption at all.
    if [ -z "$branch_span" ]; then continue; fi
    # Strip `--format <value>`/`--format=<value>` from the span before
    # running BRANCH_NAME_RE/BRANCH_RELEASE_RE against it -- `--format`'s own
    # value is a free-form display template that can coincidentally equal a
    # protected name (`git branch --format main -D feature` deletes only
    # `feature`, but the old code saw "main" and "-D" as two independent
    # matches in the same span and denied it) -- live-verified, found by
    # Codex's review of PR #177 round 2. Pure bash word-splitting (`read
    # -ra`), not a regex substitution -- no new dependency on top of the
    # jq/git/grep this file already requires, and native tokenization is
    # actually more precise here than a hand-written regex would be for
    # "skip this flag and the one token after it". Scoped to `--format`
    # specifically, the one case actually confirmed live -- `git branch`
    # has several other value-taking flags (`--sort`, `--contains`,
    # `--no-contains`, `--merged`, `--no-merged`) that could theoretically
    # share this same class of gap, but none has a confirmed live bypass, so
    # extending this fix to them speculatively is deferred rather than
    # guessed at (this scoping assumes no other reachable `git branch`
    # option consumes a separate-argument value while `-D`/delete mode is
    # also present -- unverified for `--sort` specifically, since git's own
    # mutual-exclusion checks weren't traced for every combination). Only
    # strips the literal `--format` token's own value -- the quoted-value
    # variant of this same problem (`--format='main -D'`) remains a
    # separate, already-tracked residual (issue #180), since a value
    # containing embedded whitespace inside quotes needs real shell
    # tokenization to isolate correctly, which this word-splitting approach
    # doesn't attempt. Matches only the literal token `--format`/
    # `--format=...` -- git's own accepted unambiguous abbreviations
    # (`--form`, `--forma`) aren't stripped, so `git branch --form main -D
    # feature` still over-denies; fail-safe direction, not fixed here.
    branch_name_search="$branch_span"
    if [[ "$branch_span" == *"--format"* ]]; then
      read -ra _branch_tokens <<< "$branch_span"
      _branch_filtered=()
      _skip_next_token=false
      for _tok in "${_branch_tokens[@]}"; do
        if $_skip_next_token; then _skip_next_token=false; continue; fi
        case "$_tok" in
          --format) _skip_next_token=true; continue ;;
          --format=*) continue ;;
        esac
        _branch_filtered+=("$_tok")
      done
      branch_name_search="${_branch_filtered[*]}"
    fi
    if { grep -qE "$BRANCH_NAME_RE" <<< "$branch_name_search" || grep -qE "$BRANCH_RELEASE_RE" <<< "$branch_name_search"; } \
       && { grep -qE "$BRANCH_D_RE" <<< "$branch_span" \
            || { grep -qE "$BRANCH_LOWER_D_RE" <<< "$branch_span" && grep -qE "$BRANCH_FORCE_RE" <<< "$branch_span"; }; }; then
      MATCH=true
      break
    fi
  done <<< "$BRANCH_SPANS"
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
# `-f+`/`--f(o(r(c(e)?)?)?)?`, not the exact literal `-f`/`--force` --
# `--force` is `git worktree remove`'s ONLY long option besides `--help`
# (parse-options' own auto-generated `--no-force` also exists but is
# correctly not matched -- its own internal `-f` is preceded by `o`, an
# alnum, so the leading boundary fails), so `--f` alone is already an
# unambiguous, git-accepted abbreviation (live-verified: on a dirty
# worktree, where a plain `git worktree remove <path>` genuinely fails and
# needs the flag to succeed, `git worktree remove <path> --f` succeeded);
# `-ff` (repeated) is also real, working syntax (`OPT_COUNTUP` -- git
# accepts a short flag repeated, idempotently). `-f+` matches `-f`/`-ff`/
# `-fff` (one or more literal `f` characters after the dash, nothing else)
# rather than the wider `-[A-Za-z]*f[A-Za-z]*` letter-cluster pattern
# BRANCH_FORCE_RE uses -- deliberately narrower, since `git worktree
# remove` has no other short option to legitimately bundle `-f` with (the
# wider cluster form would match an ordinary path argument like `-file` as
# a false-positive force flag, which this file's own `git branch` case
# doesn't risk the same way since branch names can't start with `-` at
# all). The long form spells out each valid prefix explicitly
# (`--f(o(r(c(e)?)?)?)?`) rather than `--f[a-z]*`, so it matches exactly
# `--f`/`--fo`/`--for`/`--forc`/`--force` and nothing past that -- a bare
# `[a-z]*` tail would also match unrelated real git flags that happen to
# start with "f" if one ever lands inside a `worktree remove` span
# (`--format`, `--file`, `--fixup`), over-denying for no reason `git
# worktree remove` itself gives grounds for.
# Leading boundary excludes `/` (`[^[:alnum:]_./-]`, not the
# `[^[:alnum:]_.-]` class GIT_PREFIX/BRANCH_D_RE use) -- a worktree PATH
# argument can legitimately end in `-f`/`--force` (`git worktree remove
# ./-f`, `git worktree remove path/--force`; `git worktree remove -h`
# documents the syntax as `[-f] <worktree>`, and git genuinely parses these
# as the positional path, not the flag, live-verified by creating and
# cleanly removing a real worktree at exactly this path with no force
# needed). The old class admitted `/` as a valid boundary the same way it
# admits a quote/paren/backtick, but nothing in this file's own history
# shows a confirmed bypass that needed `/` specifically on the LEADING
# side (only the TRAILING side's `)`/backtick widening, just below, has
# that live-verified justification) -- found by Codex's review of PR #177
# round 2. Worktree paths, unlike branch names, routinely contain `/`, so
# this leading-boundary narrowing is worktree-remove-specific and not
# applied to BRANCH_D_RE/BRANCH_FORCE_RE above, which don't face the same
# risk (git branch names can never start with `-` at all).
# Shell-conditional on whether `\` is ALSO excluded from the leading
# boundary, unlike `/` above which is excluded unconditionally -- `\` means
# two different things depending on which shell produced $COMMAND. On Bash,
# `\-f` is a legitimately backslash-escaped flag (bash's own quote
# processing reduces it to the literal two characters `-f`, still a real
# flag git receives) -- issue #85's own BRANCH_D_RE fix already needed the
# leading boundary to admit a literal backslash for exactly this reason
# (`git branch \-D main`), and narrowing it away here would reopen that
# same class of bypass for FORCE_FLAG_RE. On PowerShell, `\` is an ordinary
# Windows path separator, not an escape character (PowerShell's own escape
# character is the backtick) -- a worktree path like `.\-f` is exactly the
# same false-positive shape `/` above already fixes, just spelled with the
# platform's native separator. Live-verified both halves: `git worktree
# remove .\-f` (PowerShell) incorrectly denied before this fix; `git branch
# \-f main` (Bash, single-char flag matching FORCE_FLAG_RE's own `-f+`
# pattern) still correctly matches after it. Found by a security-reviewer
# pass on Fix B above (PR #177 round 2).
if [ "$TOOL_NAME" = "PowerShell" ]; then
  FORCE_FLAG_RE='(^|[^[:alnum:]_./\-])(-f+|--f(o(r(c(e)?)?)?)?)([^[:alnum:]_.-]|$)'
else
  FORCE_FLAG_RE='(^|[^[:alnum:]_./-])(-f+|--f(o(r(c(e)?)?)?)?)([^[:alnum:]_.-]|$)'
fi
# The `-oE` extraction below stays a pipe, not a herestring -- `grep -o`
# reads to EOF rather than exiting on first match, so it has no SIGPIPE
# exposure (issue #87 doesn't apply here); the `-qE` check just below it
# does, and uses a herestring for the same reason as the branch -D check
# above (residual: same undocumented herestring-failure fail-open as noted
# there, not caught by the ERR trap).
# Reads $COMMAND_FLAT, not raw $COMMAND -- see that variable's own
# definition above (issue #116) for why a backslash-continued command
# needed normalizing before this span extraction.
# Residual, tracked in issue #120: the span terminator class below
# (`[^;&|]`) still can't distinguish a real shell separator from the same
# byte inside two related cases the `COMMAND_FLAT` de-fang step above
# doesn't reach: (1) a quoted path containing a literal `;`/`&`/`|` (#120's
# original finding), and (2) an unquoted nested construct -- `$(...)`,
# backticks, `$((...))`, `<(...)` -- whose own body contains one of these
# bytes (e.g. `git worktree remove $(ls | head -1) --force`), which the
# span extraction has no way to treat as a single, non-terminating unit.
# Both can still truncate this span early and hide a trailing force flag.
# Properly closing either needs real shell tokenization, not a
# character-class cut -- out of scope for this fix. (The enumerated
# redirection-operator set -- `&>`/`&>>`/`>&`/`<&`/`>|` -- IS closed by the
# `COMMAND_FLAT` de-fang step above, before this span is ever extracted;
# see that step's own comment for the full operator table.)
WORKTREE_REMOVE_SPANS=$(echo "$COMMAND_FLAT" | grep -oE "${GIT_PREFIX}worktree[[:space:]]+remove[^;&|]*" || true)
if [ -n "$WORKTREE_REMOVE_SPANS" ]; then
  while IFS= read -r wt_span; do
    if [ -z "$wt_span" ]; then continue; fi
    # Truncate at the first standalone `--` token (POSIX end-of-options
    # terminator) before checking FORCE_FLAG_RE -- once `--` appears as its
    # own whitespace-bounded token, git treats everything after it as a
    # positional argument, never a flag (`git worktree remove -- -f`
    # live-verified to remove a worktree literally named `-f` with no force
    # needed, git parsing `-f` as the plain worktree name). The old check
    # scanned the whole span unconditionally, matching a force-flag-shaped
    # token anywhere, including past a real `--` -- found by Devin's review
    # of PR #177 round 2. `${wt_span%% -- *}` (bash suffix-removal, longest
    # match) finds the FIRST standalone ` -- ` and keeps only what's before
    # it; the `%%` operator prefers removing the longest matching suffix,
    # which for a `*`-terminated pattern means matching from the earliest
    # possible ` -- ` rather than the last one. That pattern requires a
    # trailing space after `--`, so it correctly does NOT match inside
    # `--format`/`--force` (whose own trailing character is never a space
    # immediately after `--`) -- only a genuinely standalone `--` token
    # trips it. The `case` fallback below covers the one shape that pattern
    # alone misses: `--` sitting at the exact end of the span with nothing
    # after it (no trailing space for ` -- *` to match against).
    # Residual, same class as issue #120's own quoted-separator residual
    # (see BRANCH_SPANS'/this variable's own earlier notes): this
    # truncation is purely textual, with no notion of quoting -- a
    # standalone ` -- ` sitting INSIDE a quoted or backslash-escaped path
    # (e.g. `git worktree remove "my -- dir" --force`) still truncates the
    # span at that point, hiding a real trailing force flag that a
    # genuine shell would correctly treat as part of a SEPARATE, later
    # argument. Found by a security-reviewer pass on this fix (PR #177
    # round 2). Not closed here, since doing so needs real shell
    # tokenization, not a character-class cut -- tracked alongside #120's
    # other already-accepted residuals in this same file.
    wt_search="${wt_span%% -- *}"
    if [ "$wt_search" = "$wt_span" ]; then
      case "$wt_span" in
        *" --") wt_search="${wt_span% --}" ;;
      esac
    fi
    if grep -qE "$FORCE_FLAG_RE" <<< "$wt_search"; then
      MATCH=true
      break
    fi
  done <<< "$WORKTREE_REMOVE_SPANS"
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
