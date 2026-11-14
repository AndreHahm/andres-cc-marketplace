# Iteration 21

New eval 18, after the pre-PR cross-model review found that the re-read right before a real close or `ignore` run covered `pr-threads` but not the PR's comments. The fix re-reads both. One simulated answer from a general-purpose subagent that read the fixed skill, graded by the author. A baseline answer from the pre-fix skill (`7354be24`, which hid `references/test-scenarios.md` from it) was also graded.

| Eval | with_skill | baseline |
|---|---|---|
| 18: a reviewer comment posted between the close approval and the real run stops the real close | 5 of 5 | 1 of 5 |

The baseline re-read only `pr-threads`, saw `unresolved_count` 0 and ran the real close without reading the new comment (failed assertions 1 to 4). It named that as a gap in the skill.
