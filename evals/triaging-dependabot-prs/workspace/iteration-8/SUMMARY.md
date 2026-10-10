# Iteration 8 (2026-10-10)

Quick Workflow, `with_skill` only, no baseline, one simulated answer, graded by the author (not blind).

| Eval | Subject | Result |
|---|---|---|
| 11 | Uncertain or mistaken write: stop, re-read, disclose, post only listed commands the user asks for (scenario 55) | 6 of 6 assertions pass |

Why this iteration exists: a review round (skill-reviewer, skilldir-reviewer) found that `references/recovery.md`
could not tell whether the skill's own comment was posted, claimed a duration for `ignore` that
`dependabot-comments.md` does not support, and offered `recreate` after a close without support. Those were
fixed, which changed rule 2 of `recovery.md`, so eval 11's assertions were revised (six instead of five) and
the eval was re-run against the revised text. Iteration 7's result applies to the earlier text only.

Only eval 11 was run. Evals 1 to 10 were not re-run.

Caveats: one simulated answer, graded by the author. Assertion 4 passes with the PR number present in the
answer's title and wrap-up rather than repeated in the step that reports what was posted. The subagent made one
read-only directory listing with Bash although it was told to use only Read and Write.
