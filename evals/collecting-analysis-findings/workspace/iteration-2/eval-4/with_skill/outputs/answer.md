# Codacy findings for PR 7 (example-org/example-repo): not collected

Status: STOPPED at normalization. No findings record was written, and no counts are reported.

- Target: PR 7 of example-org/example-repo. Current head per the user: 2222222222222222222222222222222222222222.
- Provider read: skipped by instruction (no `codacy`, `codacy-analysis` or `gh` command was run). The saved Cloud CLI output was used as the input instead:
  plugins/quality-kit/skills/collecting-analysis-findings/scripts/fixtures/unknown.json
- Normalizer: `python3 -I .../scripts/collect_codacy.py --kind pr --input .../fixtures/unknown.json --format json`
  exited 2 with `collect_codacy: pullRequest: expected an object, got NoneType`.
- The input file holds only `{"errors": ["not a Cloud CLI shape"]}`. It is not a PR analysis, so the adapter fails closed.
  The output file was discarded, as the skill requires on a non-zero exit.
- Currency check (step 5): not run. There is no record whose `source.pull_request` or `head_commit_sha` could be compared
  with the head the user reported. Nothing about the analysis can be called current or stale.

What is needed to continue: a real `codacy pull-request gh example-org example-repo 7 --output json` capture for this PR
(run by the user, or by a session allowed to run it), saved to the scratchpad and passed to the same normalizer command.
A guessed mapping was not used, because it would feed wrong numbers into a decision.
