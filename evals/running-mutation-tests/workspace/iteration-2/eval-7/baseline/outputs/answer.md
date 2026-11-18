## prefix_check.py mutation results

The mutation run on `scripts/marketplace_ci/prefix_check.py` finished cleanly, using the selection `tests/marketplace_ci/test_prefix_check.py`.

| killed | survived | timeout | not measured | score |
|---|---|---|---|---|
| 61 | 4 | 0 | 12 | 93.8 % |

- The runner and parser both exited with status 0, and the repository working tree was unchanged.
- Four mutants survived. You chose to skip all four for now.
- Twelve mutants were not measured. That count is worth a look before you rely on the 93.8 % figure, because the score covers only the measured mutants.

## Adding it to the weekly mutation run

The run has finished, so the next step is to add the module to the weekly mutation run. The weekly workflow (`.github/workflows/mutation-testing.yml`, cron `17 4 * * 1`) takes its module list from `.github/mutation-modules.yml`. Adding `prefix_check.py` there, with `tests/marketplace_ci/test_prefix_check.py` as its test selection, is a repository edit. I have not made it, because this exercise is plan-only.

Before I make that edit, I need your answer to one question:

**Question:** Should `prefix_check.py` join the weekly mutation run now, while its four surviving mutants remain unresolved?

- **Add now, leave the four survivors open.** The weekly run will report them every week until they are handled. Choose this if you want continuous visibility.
- **Hold until the survivors are addressed.** Nothing changes in CI until the four survivors are killed or explicitly accepted. Choose this if you want the weekly report to be clean from its first run.
- **Add now and record the four survivors as accepted.** This keeps the weekly report quiet while the decision stays on record. Choose this only if you have decided the four survivors are acceptable.
- **Other.** Use this for any different plan, such as a different test selection.

I have stopped here and have not edited any file or dispatched any agent.
