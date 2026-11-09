# Eval Evidence

Moved out of `SKILL.md` to keep it within its size budget (R13). The run record, activation lists and
quality gates stay in `SKILL.md`.

**Eval evidence:** `evals/collecting-analysis-findings/evals.json`, 4 scenarios (current PR, stale head,
instruction-like message, unknown shape), Full Pipeline iteration 1, 2026-10-17: with skill 14 of 14
assertions, baseline 12 of 14 (mean per-eval rate 87.5%, +12.5 points). Only 2 assertions separate the arms
(the normalized record file, and reporting that a repository list has no issue id or tool name). The
stale-head and unknown-shape evals pass for both arms, so they guard the documented behavior and do not show
an uplift. In the injection eval both arms treat the message as data; it separates the arms only on the null
issue id and tool. Iteration 2, after the audit fixes, gave the same 14 of 14 against 12 of 14 on the same
two assertions. The adapter's own behavior is covered by the smoke test.

**Sonar evidence:** evals 5 and 6, Full Pipeline, iteration 3, 2026-11-07, one run per arm, on the redacted fixtures: with skill 9 of 9 assertions, baseline 7 of 9. Only eval 5 separates the arms (the record and the two-pipe status step). Eval 6 passes for both arms, one assertion only because the baseline never mentions `is_analysing`. `scripts/smoke_test.py` passed all its checks the same day, adapter included.

**Sonar re-run after the review fixes:** evals 5 and 6 with skill only (baselines do not read this file), iteration 4, 2026-11-07: 9 of 9 assertions.

**Eval 5 after the third read:** iteration 4 predates the `--confirm` read, so its eval 5 record has no
`analysis_date` or `snapshot_consistent`. Eval 5 was re-run with skill only (Quick Workflow), iteration 5,
2026-11-09, with two added assertions for those fields: 8 of 8. Its confirm read re-used the saved PR list, so
`snapshot_consistent: true` there shows the pipe works, not that two live reads agreed.
