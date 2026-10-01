<!-- Saved by the coordinator from the eval agent's returned report; the agent had no write tool. -->
# R31 registry-completeness: foo and bar

The clause: every `evals/<skill>/workspace/iteration-*/eval-N` directory needs a matching `evals.json` entry, matched by `id`, `eval_id`, or a string id of the form `"eval-N"`. The iteration number does not matter, only N.

## foo: FINDING
- Workspace evals by N: 1, 2, 3, 4. `evals.json` ids: 1, 2, 3.
- `iteration-2/eval-4` has no entry in `evals.json`. This is the gap.
- Severity: REQUIRED, applied immediately (R31 is not forward-looking).
- Who checks: the agent reviewing the plugin, using Glob and Read. Not yet implemented in `check_evals.py`; `plugin-rulebook-checker` does not run R31 (no Bash grant).
- Fix: add an `evals.json` entry for eval 4, or remove `eval-4` if it is a stray artifact. Same shape as the known gap in `plugin-lifecycle-maintenance` (evals 10 and 11, issue #145).

## bar: NO FINDING
- Workspace evals: 1, 2. `evals.json` identifies entries with `eval_id` 1 and 2 and has no `id` key.
- The clause accepts `eval_id`, so both workspace directories match. A naive integer-`id` comparison would wrongly report two gaps.
