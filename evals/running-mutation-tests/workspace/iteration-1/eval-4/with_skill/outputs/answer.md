# Mutation run result: no score

The run finished, but the parser could not reconcile its result, so there is no score for this module.

## What the digest says

- **Repository unchanged:** yes. Nothing in the working tree was modified.
- **Runner exit status: 0.** mutmut finished.
- **Parser exit status: 2.** The parser refused to produce a score. It reports that the counts from the `.meta` files (killed: 41) and from `mutmut-cicd-stats.json` (killed: 39) do not match each other or mutmut's totals.

Per the skill's Step 3, a runner status of `0` with a parser status of `2` means: report that there is no score, and stop. I have not computed a score from the raw counts, because the parser's refusal is the fail-closed answer and the two sources disagree.

## What this means for your request

- **Weekly entry: not updated.** The skill only adds or updates a `.github/mutation-modules.yml` entry after a run whose parser produced a score (Step 5). Adding the extra test file would need a new run with that selection, and that run would also need to reconcile.
- **Module name not in the digest.** The digest does not name the module or the test selection that ran. Before any next step, the module path and selection should be confirmed from the agent's own output so the result is tied to the right entry.
- **Not measured:** not reported. The digest gives no not-measured count.

## Questions for you (not asked yet; written here as required)

1. **How should I proceed?**
   - "Re-run the same selection once" - a fresh mutation-tester dispatch with the same module and tests, to see whether the mismatch repeats.
   - "Stop and investigate the reconciliation mismatch" - no re-run; look at why the `.meta` and `mutmut-cicd-stats.json` counts differ (the parser's exit 2 is the fail-closed signal).
   - "Leave the weekly entry as is" - no run, no entry change; the module stays as it is in `.github/mutation-modules.yml`.
   - "Run with a different test selection" - add the extra test file to the selection and measure again; this counts as a new run with a new selection.

   Recommended: "Stop and investigate" first, since a repeated run with the same selection will likely hit the same mismatch.

## Next step

Nothing further is run or written in this plan-only pass. Waiting for your answer to question 1.
