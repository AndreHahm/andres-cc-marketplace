# merge-pr iteration 26 (2026-11-26)

Eval 51, issue #912: with `--stop-on-review-findings`, step 2 classifies only live bodies. A review counts
only when its `commit.oid` equals the current `headRefOid`; a conversation comment minimized as
`resolved` or `outdated` is skipped.

- with_skill: the worktree's merge-pr after the change. Baseline: the same skill on `main` at 008d9bf6.
- One plan-only general-purpose agent per arm, claude-opus-5-5, graded by the author against
  `eval_metadata.json`. No token or timing data.

| Eval | with_skill | baseline |
|---|---|---|
| 51, live bodies only | 3/3 | 1/3 |

The baseline stops on the handled review body from an earlier head and on the comment hidden as resolved,
which is the behavior issue #912 reports. Both arms stop on the comment hidden as off-topic, so the third
assertion does not separate them; it checks that the new rule did not widen the skip beyond the two reasons.
