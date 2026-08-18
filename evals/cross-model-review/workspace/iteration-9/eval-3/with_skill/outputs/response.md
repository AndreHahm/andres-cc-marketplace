# Cross-reference accuracy check: scenario count

**Claim in SKILL.md** (Testing & Validation section, lines 496-500):

> **Concrete scenarios to check, and quality gates:** see `references/testing-scenarios.md` — extracted
> per plugin-rulebook's R13 line-count threshold; the **25 numbered scenarios** and full quality-gate
> checklist live there, ...

**Actual count in `references/testing-scenarios.md`**

The "Concrete scenarios to check" section contains a numbered list running from item 1 through item 25,
with no gaps or duplicate numbers:

1. Empty diff against `$BASE`
2. `codex-kit`/`codex` CLI missing entirely
3. `codex-review-bridge` returns `isolation_profile_unavailable`, guardrails disabled
4. One-sided Phase 1 finding explicitly refuted in Phase 2
5. `prompts/review.md`/`refute.md` don't exist on `$BASE` yet
6. Diff modifies a `plugins/codex-kit/**/scripts/**` file even when `$SCOPE` excludes it
7. Claude Phase 1 finding on an excluded path
8. `git show || true` doesn't abort the chain when prompt files are missing
9. Every changed file deleted/invalid-charset (eligible list empty)
10. First-Send Confirmation answered "Stay Claude-native for this run"
11. Codex Phase 2 envelope's `dispatch.reviewer` matches `--reviewer-type` exactly
12. Diff modifies `codex-windows-guardrails/assets/...` files
13. Branch under review also modifies `prompts/review.md`
14. Phase 1 Codex succeeds, Phase 2 Codex times out (partial failure)
15. Claude finding with eligible `location` but excluded `components` entry
16. Working tree has uncommitted staged/unstaged changes
17. Change set is entirely a new, never-`git add`ed file
18. Changed path is a symlink resolving outside `$REPO_ROOT`
19. `codex-kit` genuinely not installed (single-model mode, no `envelope-schema.md`)
20. Untracked file in scope; real `git status` unaffected after run
21. Symlink resolves to a sibling directory whose name is a string-prefix of the repo root's name
22. `REVIEW_UNVERIFIED`/`REFUTE_UNVERIFIED` disclosed at First-Send Confirmation, not just in Phase 3
23. Skill invoked twice in the same session — First-Send Confirmation re-fires
24. Live-verified `[ -n "$SCOPE" ]` test-command permission grant, against this skill's own 177-file PR diff
25. Untracked file in scope — `$UNTRACKED_FILES` captured before throwaway-index switch, appended to Codex instructions

That is **25 numbered scenarios**, counted directly (1 through 25, sequential, no skips or repeats).

## Answer

**Yes, the stated count matches.** SKILL.md says "the 25 numbered scenarios ... live there," and
`references/testing-scenarios.md`'s "Concrete scenarios to check" section actually contains exactly 25
numbered items (1–25). No discrepancy found.
