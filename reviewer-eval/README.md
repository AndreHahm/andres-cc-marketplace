# Reviewer eval

Measures the reviewers behind the Codex delta review before anything about them changes (Phase 4 of
[#568](https://github.com/AndreHahm/andres-cc-marketplace/issues/568), issue
[#586](https://github.com/AndreHahm/andres-cc-marketplace/issues/586)). This phase only measures: it
never changes a reviewer prompt, pin or weight.

## Layout

| Path | Holds |
|---|---|
| `corpus/pr-<pr>-<head8>.json` | One labelled case per (PR, head commit). Validated by `scripts/reviewer_eval/corpus.py`. |

Run `uv run python -m scripts.reviewer_eval.corpus validate` to check every case.

## Case format

```json
{
  "schema_version": 1,
  "pr": 579,
  "head_sha": "<40 lowercase hex characters>",
  "kind": "findings",
  "findings": [
    {
      "id": "f1",
      "reviewer": "security",
      "path": "plugins/git-kit/scripts/git-review-ledger.py",
      "line": 38,
      "rule": null,
      "label": "true",
      "source": "ledger",
      "note": "",
      "known_issue": "k1"
    }
  ],
  "known_issues": [{"id": "k1", "path": "plugins/git-kit/scripts/git-review-ledger.py", "description": ""}]
}
```

`kind` is `findings` or `clean`. A `clean` case is a PR with no known defect: it has no `known_issues`
and no finding labelled `true`, so any finding on it counts against precision.

## Labelling rule

Every finding a reviewer reported on that head gets exactly one label:

| Label | Meaning |
|---|---|
| `true` | The defect is real and in the code the PR changed. |
| `false_positive` | The reviewer was wrong: the code does not have the defect. |
| `pre_existing` | The defect is real but was already there before the PR. |
| `out_of_scope` | Real, but outside what the PR is for or what the reviewer is meant to judge. |

Where labels come from, in order: the outcomes ledger (`.claude/review-outcomes.json`), the review
thread's outcome, then the owner's spot-check. `source` records which one decided. Only `true` counts
as a correct finding for precision; the other three do not.

Recall is measured against `known_issues`: defects that retrospective review of the PR established were
present. A finding links to the known issue it found through `known_issue`, and must be labelled
`true`. Defects are never seeded.
