# Evaluation Summary

The evidence behind the thresholds, the pinned model and the data policy. Raw answers are not kept in
this repository.

## Decision Evaluation, 2026-10-31

- **Set:** 63 labelled review decisions from this repository's own pull-request reviews: 25 real defects
  and 38 non-defects.
- **Run:** 3 repeats per model, 1,134 requests across six models, so 189 answers per model. Of those, 75
  are on real defects and 114 on non-defects.

| Model | Accuracy | Real defects passed | Non-defects blocked |
|---|---|---|---|
| `liquid/d1-ultra` (pinned) | 0.915 | 11 of 75 | 5 of 114 |
| `baseten/elephant-1` (fallback) | 0.889 | 18 of 75 | 3 of 114 |

Those rows cut `p_block` at 0.5. The shipped thresholds are stricter:

| Model | At `p_block` <= 0.05 | At `p_block` <= 0.10 |
|---|---|---|
| `liquid/d1-ultra` | 81 of 189 answers, 0 real defects | 92 of 189 answers, 3 real defects |
| `baseten/elephant-1` | 81 of 189 answers, 0 real defects | 93 of 189 answers, 0 real defects |

The 3 at 0.10 are all repeats of one security-grant defect. The set is small and comes from one kind of
decision, `safe_to_proceed` on review findings.

## Zero Data Retention Check, 2026-11-01

Both pinned snapshots answered on `/api/alpha/decisions` with `provider: {"zdr": true}` and were served
exactly. A control model that is not on OpenRouter's zero-data-retention list answered without the flag
and was refused with it, with HTTP 404. This shows enforcement on that date, not a lasting guarantee.
