## Summary
`plugins/git-kit/hooks/scripts/guard-raw-destructive-cleanup.sh` shipped a fix to its `git worktree remove --force` detection regex without the `security-reviewer` pass `.claude/rules/require-security-review-before-new-gate.md` requires before a structural change to an existing security gate's pass/fail logic — the review couldn't complete this session due to sustained `API Error: 529 Overloaded` (2 attempts, same root cause already documented in `issues/2026-08-24-phase5-audit-incomplete-reviewers-529.md`). The fix itself is extensively live-verified (see below); this issue tracks the missing process gate, not a suspected defect.

## Environment
- **Product/Service**: `git-kit` plugin (this marketplace) — the `guard-raw-destructive-cleanup.sh` `PreToolUse` hook
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
1. `plugin-lifecycle-downstream` Phase 7 (Deep Test, Scoped mode) ran `test-hook.sh` against all 6 git-kit hook scripts as part of a QA pass on 2026-08-24.
2. `guard-raw-destructive-cleanup.sh`'s `git worktree remove --force` detection was found to only block the flag-before-path argument order (`git worktree remove --force <path>`) — the equally-valid, arguably more natural path-before-flag order (`git worktree remove <path> --force`) produced no denial at all, live-verified via `test-hook.sh`.
3. The regex was fixed to check two independent conditions (both required, order-independent: command contains `git worktree remove`, AND command contains a standalone `--force`/`-f` token anywhere) rather than one combined positional regex.
4. The fix was re-verified live via `test-hook.sh` against 5 cases: path-before-flag (the bug) now blocks; flag-before-path still blocks; plain `remove` with no force flag still allows; `git branch -D main` still blocks (regression check); `git branch -d feature` still allows (regression check). All 5 passed.
5. Per `require-security-review-before-new-gate.md`, a `security-reviewer` dispatch was attempted against this file before committing — it failed twice with `API Error: 529 Overloaded`, the same sustained overload documented in `issues/2026-08-24-phase5-audit-incomplete-reviewers-529.md`. The user explicitly asked to stop retrying rather than continue into what looks like a sustained outage, and approved committing with the gate disclosed as skipped rather than leaving a real, verified bug unfixed indefinitely.

## Expected Behavior
Every structural change to an existing security-relevant gate gets a `security-reviewer` pass before its first commit.

## Actual Behavior
This one fix shipped without that review, due to infrastructure unavailability rather than a decision to skip it.

## Error Details
```
API Error: 529 Overloaded. This is a server-side issue, usually temporary — try again in a moment. If it persists, check https://status.claude.com.
```

## Impact
**Medium** — the fix closes a real, confirmed guard bypass and is well-tested via direct execution (not just the missing review layer), but a second, independent set of eyes on a security-relevant hook's regex logic — specifically checking for a similar bug class in the untouched `git branch -D` detection block just above it, and any command-injection-adjacent edge case in the two-condition `grep -qE ... && grep -qE ...` approach — has not yet happened.

## Additional Context
Found/fixed during a `plugin-lifecycle-downstream` full QA pass on `git-kit` (2026-08-24, this repo), Phase 7 (Deep Test, Scoped mode).

**To close, when Anthropic API capacity allows** (check https://status.claude.com first): dispatch `security-reviewer` against `plugins/git-kit/hooks/scripts/guard-raw-destructive-cleanup.sh`, asking it to (1) confirm the fix actually closes the path-before-flag bypass, (2) assess whether the two-independent-`grep` approach could itself introduce a new false-negative/false-positive (e.g. `--force`/`-f` appearing in an unrelated chained command or quoted argument), (3) check whether the sibling `git branch -D <protected-branch>` detection block (lines 89-97, unchanged by this fix) has the same positional-ordering bug class, and (4) flag anything else on a fresh read. If it finds a real issue, file a follow-up fix; if clean, this issue can simply be closed as "reviewed, no further action."
