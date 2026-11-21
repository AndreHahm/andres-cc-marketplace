# Iteration 22 (2026-11-20): new eval 24 after PR #804's round-4 fix

Quick Workflow, `with_skill` only, no baseline arm, model claude-opus-5-5, plan-only dry run (Read only,
nothing dispatched). Fix under test: the First-Send option is now "Skip Codex for this run", and
declining Codex is single-model mode only when no optional model returned a valid Phase 1 envelope
(SKILL.md, scenario 10 and its quality gate).

| Eval | Result |
|---|---|
| 24 Codex declined, optional model kept | 3/3 |

## Gaps surfaced, not changed

- The order of the optional-model egress question and Codex's First-Send Confirmation.
- Whether the Codex-specific disclosures still apply to Claude and an optional model when Codex is declined.
- Claude's challenger input when Codex is declined (inferred as the optional model's findings only).
