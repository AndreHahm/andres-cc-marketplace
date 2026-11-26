# merge-pr iteration 27 (2026-11-26)

Eval 51 re-run on the final text of issue #912, after the `security-reviewer` and cross-model-review
fixes. The simulated read now returns `headRefOid`, and the eval adds two checks: step 5 names each skipped
review body, and a read whose `headRefOid` differs from the pass's stops as a failed read.

- with_skill: the worktree's merge-pr at its final text. Baseline: the same skill on `main` at 008d9bf6.
- One plan-only general-purpose agent per arm, claude-opus-5-5, graded by the author against
  `eval_metadata.json`. No token or timing data.

| Eval | with_skill | baseline |
|---|---|---|
| 51, live bodies, head check, skipped bodies named | 5/5 | 1/5 |

The baseline stops on the handled earlier-head review and the resolved-minimized comment (issue #912's
behavior), never reaches step 5, and treats the head mismatch only as an extra reason to stop. Both arms stop
on the comment hidden as off-topic, so that assertion does not separate them; it checks the skip is no wider
than the two reasons.
