# Reviewer eval

Measures the reviewers behind the Codex delta review before anything about them changes (Phase 4 of
[#568](https://github.com/AndreHahm/andres-cc-marketplace/issues/568), issue
[#586](https://github.com/AndreHahm/andres-cc-marketplace/issues/586)). This phase only measures: it
never changes a reviewer prompt, pin or weight.

## Layout

| Path | Holds |
|---|---|
| `corpus/pr-<pr>-<head8>.json` | One labelled case per (PR, head commit). Validated by `scripts/reviewer_eval/corpus.py`. |
| `archive/pr-<pr>/<head8>-<run id>-<artifact id>.json` | The CI `codex-review-result` of one run, copied unchanged. |

Run `uv run python -m scripts.reviewer_eval.corpus validate` to check every case.

## Archiving CI results

GitHub keeps the `codex-review-result` artifacts for 90 days and that limit cannot be raised, so copy
them before they expire:

```bash
uv run python -m scripts.reviewer_eval.archive --pr 579
```

It archives the artifacts of every commit currently in the PR, skips a file that already exists and
never overwrites one. It only takes runs of this repository on the PR's own head branch, so a fork's
runs (its workflow file is its author's own) and the runs of a stacked PR's base are left out. A
result whose `provenance.head_sha` differs from its run's head is rejected, as is any artifact over
4 MB. A head that was force-pushed away is no longer listed by GitHub and is not archived. A re-run of a job gives one run several artifacts; each is kept, because each is a separate
sample of the same head.

## Scoring

```bash
uv run python -m scripts.reviewer_eval.score
```

Prints precision and recall per reviewer as JSON. Recall is measured against the corpus's
`known_issues`, so it reaches 1.0 overall when every known issue was derived from a finding; it only
means something once known issues are established independently of the findings.

Stability needs five repeated runs of one head, as archived result files:

```bash
uv run python -m scripts.reviewer_eval.score --stability run1.json run2.json run3.json run4.json run5.json --reviewer security-reviewer
```

Every file must carry `provenance.head_sha` and all must name the same head; otherwise the command
exits 1 and names the file. It prints that head (`head_sha`), how many runs gave the same blocking
set (`agree`) and whether that is stable (at least 4 of 5; `null` until five runs are given). No
repeated runs exist yet, so there is no baseline.

## Case format

```json
{
  "schema_version": 1,
  "pr": 579,
  "head_sha": "<40 lowercase hex characters>",
  "kind": "findings",
  "findings": [
    {"id": "f1", "reviewer": "security", "path": "scripts/git-review-ledger.py", "line": 38,
     "rule": null, "label": "true", "source": "ledger", "note": "", "known_issue": "k1"}
  ],
  "known_issues": [{"id": "k1", "path": "scripts/git-review-ledger.py", "description": ""}]
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
