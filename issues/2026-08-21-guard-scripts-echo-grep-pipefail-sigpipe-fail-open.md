## Summary
All 5 of `git-kit`'s `PreToolUse` guard hooks pipe `$COMMAND` into `grep -q` under `set -euo pipefail`. `grep -q` exits on its first match without reading the rest of stdin; if `echo`'s write to the pipe is still in progress when that happens, `echo` receives SIGPIPE/EPIPE and can return non-zero, and under `pipefail` the whole pipeline's exit status becomes that non-zero value even though `grep` genuinely matched — causing the `if`/`elif` condition to evaluate false and the guarded command to fall through to `exit 0` (allowed), for exactly the commands that should have been denied.

## Environment
- **Product/Service**: `git-kit`'s 5 `PreToolUse` guard scripts (`plugins/git-kit/hooks/scripts/`, mirrored under `.claude/hooks/scripts/`)
- **Region/Version**: this repo, found during a second `security-reviewer` pass on `guard-raw-pr-review.sh`, branch `feat/review-findings-handling`, 2026-08-21

## Reproduction Steps
Not independently reproduced against a real oversized command in this session (the reviewer that found this had no `Bash` access; this filer didn't attempt to force a real SIGPIPE either — see Impact/Additional Context for why reachability is low but nonzero). The mechanism, in principle:

1. `$COMMAND` (from `tool_input.command`) exceeds the OS pipe buffer size (64 KiB on Linux; Windows/Git Bash sizing not independently confirmed here).
2. A guarded pattern occurs early in `$COMMAND`, so `grep -q` matches and exits immediately, before `echo` has finished writing the rest of the (still-buffering) command string.
3. `echo` gets SIGPIPE/EPIPE on its next write attempt and returns non-zero.
4. Under `set -o pipefail`, the pipeline `echo "$COMMAND" | grep -q PATTERN` reports that non-zero exit even though `grep` matched — the calling `if`/`elif` sees "false" and control falls to the guard's `else exit 0` (or, for `guard-raw-pr-review.sh` specifically, the carve-out's own `!` check inverts the same way, degrading in the wrong direction there too).

This is the exact SIGPIPE-under-pipefail class this repo's own `.claude/rules/verify-tool-behavior-before-instructing.md` documents as a real, previously-found bug (PR #47's `sort | head -1` row).

## Expected Behavior
A security-relevant match check should not be able to silently report "no match" when the underlying pattern actually matched, regardless of input size.

## Actual Behavior
Every `echo "$COMMAND" | grep -q ...` construct across all 5 guard scripts (and this specific file's carve-out check) shares this fail-open risk for a sufficiently large `$COMMAND`.

## Impact
**Low-to-Medium, unverified reachability.** A multi-tens-of-KB single Bash command is unusual but not impossible (e.g. a long inline heredoc, a large embedded JSON payload, a very long GraphQL query pasted inline rather than routed through a file). `handling-review-findings`'s own `references/github-api-mechanics.md` actively steers long reply/query bodies into scratchpad files specifically to avoid shell-escaping issues — which incidentally also reduces (but doesn't eliminate) how often a single guarded command would be large enough to trigger this.

## Suggested Fix (not prescriptive)
Replace `echo "$COMMAND" | grep -qE "$PATTERN"` with a pipe-free match, e.g. Bash's native regex operator (`[[ "$COMMAND" =~ $PATTERN ]]` — the POSIX character classes already used throughout these scripts are supported by Bash's ERE engine) or a here-string (`grep -qE "$PATTERN" <<< "$COMMAND"`, which still uses a pipe internally but avoids the specific `echo`-writer-vs-`grep`-early-exit race). Apply across all 5 guard scripts' `$COMMAND` matching, not just one file, since the construct and the risk are identical everywhere it's used.

## Additional Context
Found during the same second-pass `security-reviewer` review that confirmed two prior findings (C1, C2) were genuinely fixed on `guard-raw-pr-review.sh`. Marked Major by that pass but explicitly noted as `⚠️ Unverified` (no live `Bash` access to force a real SIGPIPE at a given command size on this environment) — filed here as a shared, cross-guard concern rather than fixed inline in one file, consistent with how this same session already handled the analogous shared marker-timestamp octal bug (issue #83) and prefix-anchor gap (issue #85).
