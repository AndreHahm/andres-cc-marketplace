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
#     alone is. WORKTREE_REMOVE_SPANS' own check further below does NOT
#     need this same per-span isolation -- it has only one condition
#     (FORCE_FLAG_RE), so a hit anywhere in its blob always corresponds to
#     a real force flag inside a real worktree-remove span; the
#     cross-contamination risk here is specific to BRANCH_SPANS having two
#     independent conditions ANDed together.
COMMAND_FLAT="${COMMAND//$'\r'/}"
if [ "$TOOL_NAME" = "Bash" ]; then
  COMMAND_FLAT="${COMMAND_FLAT//$'\\\n'/}"
elif [ "$TOOL_NAME" = "PowerShell" ]; then
  COMMAND_FLAT="${COMMAND_FLAT//$'`\n'/}"
fi
COMMAND_FLAT="${COMMAND_FLAT//$'\n'/;}"

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
# shell separator from the same byte elsewhere -- a redirection operator
# (`2>&1`) or a quoted branch name containing `;`/`&`/`|` placed before the
# delete flag can truncate this span early and hide it. Properly closing
# this needs real shell tokenization, not a character-class cut -- out of
# scope for this fix, tracked in #120 for both span checks together.
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
BRANCH_NAME_RE='(^|[[:space:]])["'"'"']?(main|master|develop|release/[^[:space:]"'"'"']*)["'"'"']?([^[:alnum:]_.-]|$)'
if [ -n "$BRANCH_SPANS" ]; then
  while IFS= read -r branch_span; do
    # `if [ -n ... ]` wrapping, not `[ -z ... ] && continue` -- the latter's
    # failing `[` sits inside a `&&` list, which is exempt from both `set -e`
    # and the ERR trap; harmless today (an empty span just isn't a match),
    # but fragile in a script whose ERR trap denies unconditionally -- an
    # `if` doesn't depend on that exemption at all.
    if [ -n "$branch_span" ] && grep -qE "$BRANCH_NAME_RE" <<< "$branch_span" \
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
FORCE_FLAG_RE='(^|[^[:alnum:]_.-])(-f+|--f(o(r(c(e)?)?)?)?)([^[:alnum:]_.-]|$)'
# The `-oE` extraction below stays a pipe, not a herestring -- `grep -o`
# reads to EOF rather than exiting on first match, so it has no SIGPIPE
# exposure (issue #87 doesn't apply here); the `-qE` check just below it
# does, and uses a herestring for the same reason as the branch -D check
# above (residual: same undocumented herestring-failure fail-open as noted
# there, not caught by the ERR trap).
# Reads $COMMAND_FLAT, not raw $COMMAND -- see that variable's own
# definition above (issue #116) for why a backslash-continued command
# needed normalizing before this span extraction.
# Residual, tracked in issue #120 (extended there, not fixed here): the
# span terminator class below (`[^;&|]`) still can't distinguish a real
# shell separator from the same byte elsewhere -- a quoted path containing
# a literal `;`/`&`/`|` (#120's original finding) or a redirection operator
# like `2>&1`/`&>log` placed before the flag (a second vector onto the same
# line, found during this issue's own review) both truncate the span early
# and can hide a trailing force flag. Properly closing either needs real
# shell tokenization, not a character-class cut -- out of scope for this
# fix, which addresses the two-argument-order and flag-spelling gaps #116
# was actually filed for.
WORKTREE_REMOVE_SPANS=$(echo "$COMMAND_FLAT" | grep -oE "${GIT_PREFIX}worktree[[:space:]]+remove[^;&|]*" || true)
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
