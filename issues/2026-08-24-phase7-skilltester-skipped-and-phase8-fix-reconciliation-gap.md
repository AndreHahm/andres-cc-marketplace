## Summary
Two related, unverified-fix-closure gaps from `plugin-lifecycle-downstream`'s full QA pass on `git-kit` (2026-08-24), both concerning the 8 skills touched by Phases 2-8 (`commit`, `handling-review-findings`, `create-pr`, `explain-pr-changes`, `gh-operations`, `git-worktrees`, `git-notes`, `cross-model-review`):

1. Phase 7 (Deep Test)'s `skill-tester` blind-comparison baseline pass was skipped entirely for all 8 skills.
2. Phase 5's `skill-reviewer` reported 11 Major findings across 6 of the 8 skills; Phase 8's consolidated fix pass closed "9 non-blocking findings" total, but that count spans multiple reviewers' findings (activation-overlap, grant narrowings, reference-chain fixes, a code-block split, a stale-example correction, an encoding fix) — not a verified one-to-one closure specifically against `skill-reviewer`'s original 11. Phase 8's own re-verification re-ran `smoke-tester` and a targeted `plugin-rulebook-checker` pass, not `skill-reviewer` itself, so whether all 11 original Majors are actually closed, or whether some survive uncounted, is genuinely unknown from this session's record.

## Environment
- **Product/Service**: `plugin-lifecycle-downstream` (git-kit's own downstream QA pipeline), `skill-tester`/`skill-reviewer` agents — this repo's own tooling
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps (Item 1 — Phase 7 skip)
1. Run `plugin-lifecycle-downstream` Phase 7 (Deep Test) against the 8 touched skills, offering "Scoped" or "Full" mode.
2. Phase 7's hook-testing half ran to completion (`test-hook.sh` against all 6 hook scripts, 11 test cases, found and fixed a real guard bypass — commit `f6d04a2`).
3. The skill-side half — `skill-tester`'s blind-comparison baseline pass for the 8 touched skills — was never run. Given the hook testing had already delivered real value (a live, verified bug fix) and further agent dispatches carried a high risk of hitting the same sustained `API Error: 529 Overloaded` seen elsewhere in this session, the user explicitly chose to skip it rather than risk another long, possibly-fruitless retry cycle.

## Reproduction Steps (Item 2 — Phase 8 reconciliation gap)
1. Phase 5's `skill-reviewer` dispatch (component-mode, all 8 skills) reported 11 Major findings spread across 6 of the 8 skills — e.g. `explain-pr-changes` missing a git Bash grant (also independently confirmed by the rulebook checker), over-broad `gh api`/`gh pr` grants in `create-pr`/`gh-operations`, missing `AskUserQuestion`/`git branch`/`git add` grants in `git-worktrees`.
2. Phase 8 (Consolidated Fix) resolved "9 non-blocking findings" in one batch, drawn from multiple Phase 5 reviewers at once (not `skill-reviewer` alone): 1 activation-overlap exclusion, 2 over-broad-grant narrowings, 3 reference-chain fixes, 1 oversized-code-block split, 1 stale-example correction, 1 `encoding=utf-8` fix.
3. Phase 8's re-verification step ran `smoke-tester` (20/20 PASS, twice) and a targeted `plugin-rulebook-checker` re-check (PASS, 12 non-blocking advisories) — neither of which re-runs `skill-reviewer`'s own check categories (vagueness, structural quality, non-rulebook content issues). There is no re-dispatch of `skill-reviewer` anywhere in Phases 6, 8, or 10 confirming its original 11 Majors are now resolved.

## Expected Behavior
Every finding a dispatched reviewer raises is either fixed-and-reverified-by-that-same-reviewer-class, or explicitly carried forward as a named, tracked open item — not left in a state where a batch fix count ("9 resolved") could plausibly, but unverifiably, cover a different reviewer's full finding list ("11 Majors").

## Actual Behavior
- Item 1: `skill-tester` never ran against any of the 8 skills this session — no behavioral-equivalence baseline exists for any of the changes made to them across 13 commits.
- Item 2: it's unknown whether all 11 of `skill-reviewer`'s original Phase 5 Majors are closed. Phase 8's own "deliberately_not_fixed" note names exactly 2 items as intentionally left open (`dependency-reviewer`'s 2 bidirectional pairs, `create-pr`'s pre-existing ambiguous-grant advisory) — implying everything else was addressed — but this is an inference from the absence of a stated exception, not a positive confirmation from re-running `skill-reviewer` itself.

## Error Details
```
(not applicable -- both items are coverage/verification gaps, not errors)
```

## Impact
**Low-Medium** — the 8 touched skills did get substantial reviewer coverage this session (`skill-reviewer`, `skilldir-reviewer`, `scripts-reviewer`, `activation-reviewer`, `dependency-reviewer`, `plugin-rulebook-checker`, `plugin_validator` all ran against them at least once), and every rulebook-REQUIRED and structurally-Critical finding was independently re-verified. The gap is specifically: (a) no behavioral-baseline test coverage (`skill-tester`) for any of the 8, and (b) no positive re-confirmation that `skill-reviewer`'s own specific 11 Majors are fully closed, as opposed to inferred-closed from an unrelated fix-count and a targeted rulebook re-check.

## Additional Context
Found during a `plugin-lifecycle-downstream` full QA pass on `git-kit` (2026-08-24, this repo), Phase 7 (Deep Test, item 1) and Phase 8 (Consolidated Fix, item 2 — surfaced only in retrospect while auditing this session's own open items for issue-draft coverage).

**Distinct from other filed issues:** this is not the same gap as `issues/2026-08-24-phase5-audit-incomplete-reviewers-529.md` (which covers 3 reviewers that were *dispatched but 529'd*, not *never re-dispatched for verification*), nor `issues/2026-08-24-phase5-scope-16-of-24-components-never-reviewed.md` (which covers the 16 components *never reviewed at all*, whereas this issue's 8 skills *were* reviewed — the gap here is fix-closure verification, not initial coverage).

**To close, in a future session**:
1. Run `skill-tester` in blind-comparison mode against the 8 skills listed above, persisting results to `evals/<skill-name>/` per this repo's own testing convention.
2. Re-dispatch `skill-reviewer` against the same 8 skills' current (post-Phase-8) state and diff its new findings against the original 11 Majors from Phase 5, to positively confirm closure rather than inferring it.
