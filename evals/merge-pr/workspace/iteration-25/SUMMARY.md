# merge-pr iteration 25 (2026-11-26)

Evals 49 and 50, added by PR #909's last open items: step 2 reads review threads through
`git-review-api.py threads` (security-review m4), and `headRefOid` is checked against `^[0-9a-f]{40}$`.

- with_skill: the worktree's merge-pr after the change. Baseline: the same skill at e5f24004, before it.
- One plan-only general-purpose agent per arm, claude-opus-5-5, graded by the author against
  `eval_metadata.json`. No token or timing data.

| Eval | with_skill | baseline |
|---|---|---|
| 49, thread read and pagination | 4/4 | 1/4 |
| 50, malformed headRefOid | 3/3 | 3/3 |

Eval 49 separates the arms: the baseline sends a raw `gh api graphql` call with the `gh-pr-review` marker
and passes the cursor with `-f cursor=`. Eval 50 does not: the baseline also stopped at step 1, through
the skill's general data-only rule rather than an explicit check, and said so itself. It shows the
explicit gate produces the stop; it does not show a measured gain.
