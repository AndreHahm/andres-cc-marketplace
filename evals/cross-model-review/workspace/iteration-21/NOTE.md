# Iteration 21 (2026-11-20): eval 19 after PR #804's round-2 fix

Quick Workflow, `with_skill` only, no baseline arm, model claude-opus-5-5, plan-only dry run (Read only,
nothing dispatched). Fix since iteration 20, from a Critical Codex security finding: on
`secret_paths_unconfirmed`, the egress question names every path of the flagged batch with the dispatcher's
count, and the caller never reads reviewadapters-kit's own skill or references to narrow it (in this
repository's sessions that text can be the reviewed branch's). Eval 19's third assertion and expected output
changed to match.

| Eval | Result |
|---|---|
| 19 pick limit; dry-run failures; every path of the flagged batch named | 4/4 |

## Gaps surfaced, not changed

- Whether an approved planner run lifts `PLANNER_TOUCHED` for optional models.
- What to do if the flagged batch's re-run with `--secret-paths-confirmed` fails.
