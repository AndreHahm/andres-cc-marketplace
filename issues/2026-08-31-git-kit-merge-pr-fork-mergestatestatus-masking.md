## Summary

`merge-pr`'s fork-PR not-behind-base fallback (`mergeStateStatus`) can't distinguish a genuinely
current fork branch from one that's behind base but reported as `BLOCKED`/`UNSTABLE` instead.

## Environment

- **Product/Service**: `git-kit` plugin, `merge-pr` skill's step 2 "Not behind base" check (fork-PR /
  `isCrossRepository: true` branch)
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps

1. Read `plugins/git-kit/skills/merge-pr/SKILL.md`'s step 2, "Not behind base" bullet, the
   `isCrossRepository: true` branch: for a fork PR, the compare-endpoint call is skipped (unsafe to
   run by branch name), and the check falls back to the already-fetched `mergeStateStatus` field
   instead — `BEHIND` blocks, `UNKNOWN` polls (up to 5 times) then blocks if still unresolved, and any
   *other* terminal value (`CLEAN`, `BLOCKED`, `DIRTY`, `UNSTABLE`, `HAS_HOOKS`) is treated as passing.
2. Consider a fork PR that is genuinely behind its base *and* separately blocked by a branch-protection
   condition this skill doesn't independently model (e.g. required linear history, an admin-only merge
   restriction).
3. `mergeStateStatus` is a single aggregate enum value GitHub computes — it cannot represent multiple
   simultaneous conditions. GitHub may report `BLOCKED` (or another non-`BEHIND` value) instead of
   `BEHIND` for this PR, since the aggregate field can only ever surface one state at a time.
4. The not-behind-base check reads that value, sees it isn't `BEHIND`/`UNKNOWN`, and treats the gate as
   passing — even though the branch actually is behind.

## Expected Behavior

For a fork PR, the not-behind-base check should reliably detect staleness regardless of what other
merge-state condition is simultaneously true, without relying on an aggregate field whose reported
value depends on GitHub's own internal precedence between competing conditions.

## Actual Behavior

A stale fork PR that also happens to be `BLOCKED`/`UNSTABLE`/etc. for an unrelated reason can pass the
not-behind-base gate silently.

## Error Details

```
N/A -- a design gap in the readiness check's own logic, not a runtime error.
```

## Visual Evidence

N/A

## Impact

**High** — a stale fork PR can pass a blocking gate specifically meant to catch that. Partially
mitigated: the raw `mergeStateStatus` value is still surfaced unconditionally via the skill's own
*separate*, already-existing advisory disclosure at step 5's merge confirmation — a user confirming
the merge would still see e.g. `mergeStateStatus: BLOCKED` even though the not-behind-base gate itself
passed. This is visibility, not blocking, for the compound-condition case — the gap is real, but a
human confirming the merge isn't fully blind to it.

## Additional Context

Suggested fix direction (from the reviewers, not yet designed or verified): compare the fork's actual
commit ancestry directly rather than inferring from the aggregate enum — e.g. resolve the fork branch's
head OID (already partially available via `headRefOid`) and compare it against the base branch using a
cross-repository-safe compare form, then fail closed if that comparison itself is unavailable or
indeterminate. This needs real design work before implementing — specifically verifying GitHub's
compare-endpoint behavior for a SHA-based cross-repo comparison, and confirming it doesn't share the
ref-name-ambiguity risk the branch-name form has (the same risk that made a direct compare-by-name
unsafe for forks in the first place).

Independently raised by two automated PR reviewers during PR #269's automated review (2026-08-31):
Devin ("Blocked fork branches pass freshness gate") and the Codex connector ("Compare fork commits
directly before passing the stale gate", marked P1). Triaged via `handling-review-findings`; filed as
its own tracked issue by explicit user choice rather than fixed in-session or declined, since a proper
fix needs non-trivial design work that PR's already-long review chain shouldn't be extended further to
cover.

## Review Finding Source

- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/269
- **Thread/comment IDs**: 3896199247 (Devin), 3896243700 (Codex connector)
- **Reviewers**: Devin (`devin-ai-integration[bot]`), Codex (`chatgpt-codex-connector[bot]`)
- **Stated severity**: Devin — `bug` kind; Codex — P1
