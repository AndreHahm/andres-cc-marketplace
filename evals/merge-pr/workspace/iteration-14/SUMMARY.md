# merge-pr iteration 14 (2026-11-23)

Quick Workflow (skill-tester), with_skill only, no baseline arm, plan-only simulated prompts.
Target: the PR #859 branch copy of `plugins/git-kit/skills/merge-pr/` (SKILL.md and
`references/session-open-items-and-body-check.md`), read directly, not dispatched by name.

| Eval | Behavior | Result |
|---|---|---|
| 29 | Step 1.5 with nothing open continues to step 1.6 | 2/2 |
| 30 | A step-1.5 push that did not land re-runs step 1.6, then stops before step 2 | 3/3 |
| 31 | One opt-in before per-item issue drafting; a free-text reply drafts nothing | 3/3 |
| 32 | Mirror-path waiver check from the verified root; a PR that edits the checker needs approval | 2/2 |

Total: 10 of 10. With no baseline arm this shows the new text produces the intended plan; it does
not show the skill beats the pre-change text.

Observation (eval 32): the skill says not to use the pre-approved form when the PR edits the checker,
but does not name the alternative form; the agent chose a full absolute path. Its example path was
replaced with `<repo-root>` before commit (no local identifiers in committed outputs).
