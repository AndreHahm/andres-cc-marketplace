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
| `stability/pr-<pr>-<head8>/run<n>.json` | One local repeat run of that head, the `run-codex-review` result unchanged. |
| `stability/baseline.json` | The stability baseline: per head and reviewer, how many repeats agreed, with the pins used. |

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

Each file must be a different run (the same file twice, under any path or link, is refused) and
must carry a `provenance.head_sha` (40 lowercase hex characters) and a `reviewers` roster that
lists `--reviewer`. All files must also match the first one on the head, the base (`base_sha`), the
reviewed paths and the recorded model and CLI pins (`configured_model`, `pinned_cli_version`); a
field one run records and another does not counts as different. A run without both pins, a
`base_sha` of 40 lowercase hex characters, or a `reviewed_paths` list of strings is refused even
when every run lacks it, since runs agreeing on a missing value say nothing about what ran. The reviewers' own report about
themselves (`model`, `cli_version`) is not compared: under the same pins it varied between runs
(`cli_version` was `""`, `unknown` and `codex-cli 0.170.0` in five runs of one head), so it is not
evidence of what ran.
Otherwise the command exits 1 and names the file. A merged finding counts for every reviewer in its
`reporters`. It prints the head (`head_sha`), how many runs gave the same blocking set (`agree`)
and whether that is stable (at least 4 of 5; `null` until five runs are given).

### Baseline (2026-11-21)

`stability/baseline.json` holds five repeats on each of three heads (PRs #798, #799 and #805),
with `configured_model` `gpt-6-luna` and `pinned_cli_version` `0.170.0`. Every (head, reviewer)
pair was stable: 5 of 5 agreed, except `skill-reviewer` on #798, `plugin-rulebook-checker` on #799
and `security-reviewer` on #805 (4 of 5 each, where one run added a blocking finding the other four
did not raise). The runs were made locally with a ChatGPT login, not CI's API key, so the auth path
differs from CI's. PR #579's heads were not used: the dispatcher reads its reviewer files from the
checkout, so they would have measured the October roster. PRs #800 and #806 were tried and dropped:
neither started any reviewer.

`pinned_cli_version` is the version CI installs (`review_contract.CODEX_CLI_VERSION`), not a
measurement: `run-codex-review` does not check the `codex` on `PATH`, so `--stability` cannot tell
runs under different installed CLIs apart. For this baseline, `codex --version` printed
`codex-cli 0.170.0` before the runs, and the CLI was not changed during them; no run file records
that.

To repeat, run this in a checkout of each head, with `codex` 0.170.0 on `PATH` and `BASE_SHA` set
to that head's `base_sha` from `baseline.json` (its merge-base with `main` when the runs were made).
The runs go one after another, each to its own file: `--output` overwrites an existing file. Without
`CODEX_KIT_REVIEW_MODEL` the run records no `configured_model`, and `--stability` refuses it.

```bash
for n in 1 2 3 4 5; do
  CODEX_KIT_REVIEW_MODEL=gpt-6-luna CODEX_KIT_REVIEW_TIMEOUT_MS=720000 \
    uv run python -m scripts.marketplace_ci run-codex-review \
    --base-sha "$BASE_SHA" --output "run$n.json"
done
```

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

Where labels come from, in order: the outcomes ledger (`.claude/review-outcomes/pr-<N>.json`), the review
thread's outcome, then the owner's spot-check. `source` records which one decided. Only `true` counts
as a correct finding for precision; the other three do not.

Recall is measured against `known_issues`: defects that retrospective review of the PR established were
present. A finding links to the known issue it found through `known_issue`, and must be labelled
`true`. Defects are never seeded.
