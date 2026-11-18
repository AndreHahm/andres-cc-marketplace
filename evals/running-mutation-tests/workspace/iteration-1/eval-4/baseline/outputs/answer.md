## Mutation test result: no score

The mutation run finished, but the result could not be turned into a score.

- **Runner:** exit status 0. mutmut finished.
- **Parser:** exit status 2. `qlty-mutation-parse` reported that the result could not be reconciled with mutmut's totals. It counted 41 killed `.meta` files and 39 killed entries in `mutmut-cicd-stats.json`, and gave no score.
- **Repository:** unchanged. The mutation-tester ran in a scratch copy, so the working tree was not touched.

Because the parser failed, there is no survivor list and no score to record. I have not run anything again and have not changed any file.

### Question for you

Your earlier request was to update the weekly entry with one added test file if the run finished. The runner finished, but the parser did not produce a result, so I have not updated the weekly entry. How should I proceed?

1. **Hold the weekly entry** — Do not update it. Investigate the parser mismatch first (read-only), then decide.
2. **Investigate, then rerun** — Find out why the `.meta` count (41) and the stats count (39) disagree, then run mutation tests again once the cause is known.
3. **Record the failure** — Write the parser failure into the weekly entry as a note, with no score, and leave the test file out.
4. **Update anyway** — Add the test file to the weekly entry and mark the score as unavailable.

Options are listed for your choice. I am stopping here until you answer.
