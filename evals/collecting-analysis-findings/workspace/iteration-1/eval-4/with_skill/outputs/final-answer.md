# Codacy findings for example-org/example-repo PR 7: not collected

The adapter stopped with exit 2, so there is no findings record and no counts.

- Command: `python3 -I -B scripts/collect_codacy.py --kind pr --input scripts/fixtures/unknown.json`
- stderr: `collect_codacy: pullRequest: expected an object, got NoneType`
- The input file contains only `{"errors": ["not a Cloud CLI shape"]}`. It is not Cloud CLI output for a PR.
- The skill says to fail closed here, because a guessed mapping would feed wrong numbers to a decision. I discarded the partial output file and wrote no record.
- Currency check: not applicable, because there is no record to compare. The `gh pr view` re-read was skipped because the sandbox forbids `gh`. The supplied head, 2222222222222222222222222222222222222222, therefore could not be compared with a recorded head.

Next step: re-export the PR's real `codacy pull-request gh example-org example-repo 7 --output json` output, then re-run.
