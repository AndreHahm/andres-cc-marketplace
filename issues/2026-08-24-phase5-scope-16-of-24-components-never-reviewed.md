## Summary
`plugin-lifecycle-downstream`'s full QA pass on `git-kit` (2026-08-24) never individually reviewed 16 of the plugin's 24 components — 12 of 20 skills, all 4 commands, the hooks (6 scripts + `hooks.json`), and all 5 project-level rules received zero dispatch from any reviewer agent at any phase this session. This is the direct root cause of Phase 11 (Grading) refusing to produce a numeric score for the plugin (see `.claude/output/plugin-grader/git-kit-2026-08-24T08-25-44Z.json`), and is a distinct gap from `issues/2026-08-24-phase5-audit-incomplete-reviewers-529.md`, which covers only the 3 reviewers that were *attempted* (and 529'd) against the 8 skills that *were* in scope.

## Environment
- **Product/Service**: `plugin-lifecycle-downstream` (git-kit's own downstream QA pipeline), `plugin-auditor`/reviewer-agent dispatch — this repo's own tooling, not an external service
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
1. Run `plugin-lifecycle-downstream` in full/whole-plugin mode against `git-kit` (24 total components: 20 skills, 4 commands, hooks, 5 rules, `.claude-plugin/plugin.json`).
2. At Phase 5 (Audit), a full plugin-mode audit would dispatch the type-matched reviewer for each of the 24 components individually (component-mode) plus 4 whole-plugin cross-cutting reviewers (`activation-reviewer`, `consistency-reviewer`, `dependency-reviewer`, `plugin_validator`) — roughly 150+ total dispatches per `plugin-auditor`'s own dispatch table.
3. Given the session had already run well past a typical single-session budget (Phases 2-4 alone had consumed several hours across multiple fix-and-recheck rounds), the user was asked via `AskUserQuestion` whether to run the full ~150+-dispatch audit or a scoped alternative, and explicitly confirmed the scoped alternative: component-mode review for only the 8 skills touched by Phases 2-4's fixes (`commit`, `handling-review-findings`, `create-pr`, `explain-pr-changes`, `gh-operations`, `git-worktrees`, `git-notes`, `cross-model-review`), plus the 4 whole-plugin reviewers (which inherently need whole-plugin scope regardless of which skills were touched).
4. This was a deliberate, disclosed, user-confirmed scope reduction at the time — not a silent gap. But its consequence is that 16 components never received any reviewer's attention this session, at any phase: `codex-review-recovery`, `collaborating-on-a-pr`, `dependency-updater`, `finishing-work`, `git-bisect`, `git-cleanup`, `git-rebase-sync`, `github-issue-creator`, `manage-codeowners`, `merge-pr`, `standalone-commits`, `starting-work` (12 skills); `create-git-git-local-json`, `git-status`, `sync-branch`, `update-branch-name` (4 commands); all 6 hook scripts + `hooks.json`; all 5 `.claude/rules/*.md` files.
5. Phase 11 (Grading) subsequently invoked `plugin-grader` in evidence-only mode and refused to compute a `plugin_final_score`, citing exactly this coverage gap (8/24 components) as one of its two disqualifying reasons.

## Expected Behavior
Either a full plugin-mode audit covers all 24 components (enabling a real whole-plugin grade), or a scoped audit's coverage gap is tracked as its own explicit, actionable item — not left implicit inside a scope-narrowing decision that reads as "resolved" once the 8-skill scope's own findings are fixed.

## Actual Behavior
The scope-narrowing decision and its consequence were recorded in `scope.json`'s `phase_5_audit` block (`scope_narrowed_from_full_plugin_mode: true` and its accompanying `scope_narrowing_reason`) and in this session's build-handoff report, but never surfaced as a standalone, independently trackable issue — someone scanning only `issues/*.md` for open work on `git-kit` would not learn that 16 of its 24 components have never been reviewed by any `plugin-devkit` reviewer.

## Error Details
```
(not applicable -- this is a coverage gap from a deliberate scoping decision, not an error)
```

## Impact
**Medium-High** — this is the single largest open item from this session. It is the direct cause of Phase 11's grading refusal (a "cannot score responsibly" outcome, not evidence of a defect), and it means 16 components — including all 4 slash commands, all 6 hook scripts (which enforce this plugin's own security-relevant guard behavior), and all 5 project rules — have had no `plugin-rulebook-checker`, `skill-reviewer`/`command-reviewer`/`hook-reviewer`/`rule-reviewer`, `security-reviewer`, `completeness-reviewer`, or `skilldir-reviewer` pass at all, ever, in this plugin's tracked history (the last prior full sweep predates this session per the plugin's own README maintenance log). There is no specific reason to suspect any of the 16 has a defect — this is an absence of evidence, not evidence of absence.

## Additional Context
Found during a `plugin-lifecycle-downstream` full QA pass on `git-kit` (2026-08-24, this repo), across Phase 5 (Audit, where the scope was narrowed) and Phase 11 (Grading, where the consequence surfaced as a refusal).

**Related, already-filed issue with a narrower scope:** `issues/2026-08-24-phase5-audit-incomplete-reviewers-529.md` covers 3 reviewers (`security-reviewer`, `completeness-reviewer`, `consistency-reviewer`) that *were* dispatched against the *8 in-scope* skills but hit sustained `API Error: 529 Overloaded` and never completed. That issue's retry scope is exactly those 8 skills. This issue is about the other 16 components that were never even attempted — retrying the 3 reviewers from that issue would not close this gap.

**To close, in a future session**: run `plugin-auditor` (the actual skill, not ad hoc direct reviewer dispatches — see `issues/2026-08-24-...` grading-refusal context in the Phase 11 report) in full plugin mode against `git-kit`, covering all 24 components. This both closes the coverage gap directly and produces a real, persisted, individually-provenanced `plugin-auditor` Report Revision that a future `plugin-grader` evidence-only pass can actually score against — which this session's Phase 11 could not do, for exactly this reason.
