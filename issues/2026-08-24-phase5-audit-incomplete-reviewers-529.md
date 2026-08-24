## Summary
`plugin-lifecycle-downstream` Phase 5 (Audit) on `git-kit` could not complete 3 of its 10 planned reviewer dispatches — `security-reviewer`, `completeness-reviewer`, and `consistency-reviewer`, each scoped to the 8 recently-touched skills (`commit`, `handling-review-findings`, `create-pr`, `explain-pr-changes`, `gh-operations`, `git-worktrees`, `git-notes`, `cross-model-review`) — due to sustained `API Error: 529 Overloaded` from the Anthropic API, not a design or scoping choice. Recorded here per `plugin-lifecycle-downstream`'s own "Optional work is never implied to have passed" discipline, and so the retry scope is preserved for whenever capacity allows.

## Environment
- **Product/Service**: Anthropic API (backend serving Claude Code subagent dispatches) — not a `git-kit` or marketplace-repo issue
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
1. Dispatch `security-reviewer` (or `completeness-reviewer`/`consistency-reviewer`) as a background `Agent` targeting the 8 skills listed above, in the `plugin-lifecycle-downstream` worktree for this run.
2. Each of the 3 reviewers was retried 4-5 times across roughly 40 minutes of wall-clock time, every attempt terminating with the same error before producing any output.
3. Meanwhile, the other 7 Phase 5 reviewers dispatched in the same batch (`plugin-rulebook-checker`, `activation-reviewer`, `dependency-reviewer`, `skill-reviewer`, `skilldir-reviewer`, `scripts-reviewer`, `plugin-validator`) all completed successfully — several after their own single 529 retry — indicating the overload was intermittent/sustained across the session's dispatch window rather than a hard, permanent outage.

## Expected Behavior
All 10 planned Phase 5 reviewer dispatches complete and contribute findings to the audit rollup.

## Actual Behavior
3 reviewers never returned a result; every attempt errored with `API Error: 529 Overloaded. This is a server-side issue, usually temporary — try again in a moment. If it persists, check https://status.claude.com.` The user explicitly asked to stop retrying rather than continue indefinitely into what looked like a sustained overload window.

## Error Details
```
API Error: 529 Overloaded. This is a server-side issue, usually temporary — try again in a moment. If it persists, check https://status.claude.com.
```

## Impact
**Medium** — this is a coverage gap in Phase 5's audit, not a known defect in `git-kit` itself. The 7 completed reviewers already surfaced substantial findings (5 REQUIRED rulebook violations, several Major findings across activation/dependency/scripts/skill-quality axes), so the audit as a whole is not empty — but permission-risk, prompt-injection, completeness, and cross-skill-consistency coverage specifically for the 8 touched skills was never obtained in this run.

## Additional Context
Found during a `plugin-lifecycle-downstream` full QA pass on `git-kit` (2026-08-24, this repo), Phase 5 (Audit), scoped-review mode (component-mode dispatch for the 8 touched skills + 4 whole-plugin cross-cutting reviewers, per a user-confirmed scope narrowing from full plugin-mode's ~150+ dispatches).

**To retry, when Anthropic API capacity allows** (check https://status.claude.com first), dispatch these 3 with the same scope:

1. **`security-reviewer`** — permission risk, prompt-injection surface, and credential-leakage patterns across `commit`, `handling-review-findings`, `create-pr`, `explain-pr-changes`, `gh-operations`, `git-worktrees`, `git-notes`, `cross-model-review`. Note: this is a fresh full-plugin-adjacent pass, distinct from the 4 rounds of deep security review already completed specifically on `commit`'s trust-boundary/staging logic (tracked separately in `issues/2026-08-24-commit-skill-remaining-shell-injection-surfaces.md`).
2. **`completeness-reviewer`** — open items, missing documentation, missing test/validation evidence, and stale information across the same 8 skills.
3. **`consistency-reviewer`** — data/governance/functionality/capability drift across the same 8 skills, with particular attention to whether `commit`'s and `handling-review-findings`' independently-implemented (deliberately not shared) `.claude/git-kit.local.json` trust-boundary check logic stays consistent, and whether any other skill reading that file (e.g. `starting-work`) has a stale or divergent version of the same check.

Once these 3 complete, fold their findings into the Phase 5 audit rollup (or a follow-on Phase 6 fix pass) alongside the 7 already-completed reviewers' results from this run.
