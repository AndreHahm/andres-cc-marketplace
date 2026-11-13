## Summary
Two one-way activation overlaps: `cross-model-review` claims "second-opinion review" without limiting it to a diff, and `github-issue-lifecycle` does not send follow-up issues from a Notion decision to `open-item-management`.

## Environment
- **Product/Service**: git-kit plugin, `plugins/git-kit/skills/cross-model-review/SKILL.md` and `plugins/git-kit/skills/github-issue-lifecycle/SKILL.md`; plugin-rulebook rule R36 (reciprocal exclusions, ADVISORY)
- **Region/Version**: current `main`; found by an `activation-reviewer` pass on 2026-11-13 during branch `docs/resolve-rulebook-advisories-batch` (commits 345fe34c, e1249584) and left out of it to keep its scope

## Reproduction Steps
1. Open `cross-model-review/SKILL.md`. Line 11 of the description says "Use for an adversarial review, a cross-model or second-opinion review", and line 51 repeats "second-opinion review". Neither limits it to the working diff.
2. Read its "When NOT to Use": it does not name `codex-peer-review` or `codex-verify`.
3. Open `github-issue-lifecycle/SKILL.md`. Its "When NOT to Use" has no line for follow-up issues that start from a Notion Report or Decision, or from a completed Linear issue.

## Expected Behavior
- "get a codex second opinion on this design" routes to `codex-peer-review` only, and `cross-model-review` says so in its own exclusions.
- "create follow-up issues from this Notion decision" routes to workmanagement-kit's `open-item-management` only, and `github-issue-lifecycle` says so in its own exclusions.

## Actual Behavior
- Item 1 (rated Major by the reviewer): `cross-model-review`'s unqualified "second-opinion review" overlaps `codex-peer-review`'s triggers. A routing eval (`evals/consulting-decision-model/workspace/routing-iteration-1/`) picked `codex-peer-review` correctly with both the old and the new text, but both judging agents still named `cross-model-review` as a partial match.
- Item 2 (Minor): `open-item-management` already owns this case, but `github-issue-lifecycle`'s "Filing a new issue" use case has nothing that defers to it.

## Impact
**Medium** - routing wording only; no live misroute has been observed. Item 1 is the more likely to misfire because the shared phrase is a trigger phrase on both sides.

## Additional Context
- Proposed fix, item 1: change the description to "a cross-model or second-opinion review of the working diff"; add "When NOT to Use" lines for `codex-peer-review` (a design, analysis or recommendation with no diff) and `codex-verify` (an existing plan or document file); add matching "does NOT activate on" phrases. `cross-model-review/SKILL.md` is at 490 lines, the R13 warning threshold, so keep the additions line-neutral or extract something to `references/`.
- Proposed fix, item 2: one "When NOT to Use" line in `github-issue-lifecycle` naming `open-item-management`, plus a "does NOT activate on" phrase.
- Edit the `plugins/` copies and sync the `.claude/` mirrors, which must stay byte-identical.
- Related: #647 and #477 (the reciprocal exclusions fixed on that branch).
