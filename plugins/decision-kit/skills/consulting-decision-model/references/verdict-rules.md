# Verdict Rules

`dck-decide.py` applies these rules, so Claude never has to judge the numbers itself. `p_block` is
`1 - safe_to_proceed`. `no_stop` means the model adds no stop; it authorizes nothing, so Claude still
asks wherever it would have asked without this check.

| Claude's position | `p_block` | Extra checks | Verdict | `reason` |
|---|---|---|---|---|
| proceed | at or below `proceed_max_p_block` | option and risk match | `no_stop` | `agree` |
| proceed | at or below `proceed_max_p_block` | model's option differs | `ask_user` | `disagree_on_option` |
| proceed | at or below `proceed_max_p_block` | model's risk is higher | `ask_user` | `disagree_on_risk` |
| proceed | between the thresholds | | `ask_user` | `uncertain` |
| proceed | at or above `stop_min_p_block` | | `ask_user` | `disagree` |
| stop | at or above `stop_min_p_block` | | `ask_user` | `agree_stop` |
| stop | between the thresholds | | `ask_user` | `uncertain` |
| stop | at or below `proceed_max_p_block` | | `ask_user` | `disagree` |

The risk score is an expected value on the rubric's index scale, so it is read as its nearest step
before comparing it with `claude_risk`.

## Thresholds

The defaults are 0.05 and 0.8. On the 189 answers per model in the
[evaluation of 2026-10-31](evaluation-summary.md), neither
model passed a real defect at 0.05, and about 43% of decisions fell at or below it. At 0.10 the
pinned model passed a security-grant defect in all 3 repeats. Zero of 75 is small-sample evidence, not
proof. Only `safe_to_proceed` was measured: the option and risk comparisons have no measured evidence,
so a mismatch on either asks the user.

## Model Failures

The pinned model and the fallback are each tried once.

| Result from the pinned model | Next step |
|---|---|
| No response, 404, 429, 500, 502, 503, 524, 529, or a malformed or wrong-model answer | Try the fallback |
| 400 "does not exist" | Try the fallback, and warn to re-pin |
| `expiration_date` set in the model list | Skip it, use the fallback, and warn to re-pin |
| 401, 402, 403, 413, or any other status | Unavailable, because the fallback would fail the same way |

A 404 is also how the API refuses a model with no ZDR endpoint. The fallback runs under the same flag,
so this cannot weaken the data policy.

A missing or malformed key counts as no answer and sends nothing. If the fallback itself has an
expiration date, it is still used, with a warning to choose a new one. With both models, the worst case
is about 45 seconds.

When no answer is obtained, a `confidence` decision with a `claude_risk` below `high` returns
`no_second_opinion`. Everything else returns `ask_user` with `reason: unavailable`.

## Other Outcomes

| Situation | Verdict | `reason` |
|---|---|---|
| `enabled` is off, on a critical, security or high-risk decision | `ask_user` | `disabled` |
| `enabled` is off, otherwise | `disabled` | `disabled` |
| The script hits an unexpected error | `ask_user` | `internal_error` |
