# Iteration 24

New eval 21, after the CI gate gained the actions pin exemption (`docs/ci.md`): a verified Dependabot
`github_actions` PR whose every changed line swaps a ratchet-pinned `uses:` SHA for the commit its tag names now
passes `Hygiene (PR contract)` and `Publish Codex policy result`. The skill's references used to say such a PR is
always expected to fail and should be skipped. One simulated answer from a general-purpose subagent that read the
updated skill and the `docs/ci.md` exemption, graded by the author. A baseline answer from the pre-change skill
(`1894953b`, its SKILL.md and references only) was also graded.

| Eval | with_skill | baseline |
|---|---|---|
| 21: Actions pin-only bump goes through the loop; any other workflow change is skipped | 5 of 5 | 1 of 5 |

The baseline skipped #601 at step 6.2 with no rebase, required-CI read or `merge-pr` call, and its wrap-up
listed both PRs as skipped; only its #602 handling matched (assertion 4).
