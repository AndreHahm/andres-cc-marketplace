## Summary

`issue-auto-labeler-batch-run.yml` and `pr-auto-label-batch-run.yml` can only ever label the newest
`limit` matching issues/PRs on a given run — there's no cursor, offset, or exclusion mechanism, so a
rerun with the same inputs re-fetches the exact same set. A repo with more un-labeled items than
`limit` can never have the older ones reached by these batch workflows.

## Environment

- **Product/Service**: GitHub Actions batch-label workflows (`issue-auto-labeler-batch-run.yml`,
  `pr-auto-label-batch-run.yml`)
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps

1. Have more open (or `process_all: true`) issues/PRs than the `limit` input (default 100) that lack
   the labels these workflows would apply.
2. Run either batch workflow once — it labels the newest `limit` matching items.
3. Run it again with the same inputs.
4. Observe: the same items are selected again (`gh issue list`/`gh pr list` sort newest-first with no
   way to skip already-processed items), so the older, unlabeled items are never reached.

## Expected Behavior

Either the workflow should be able to advance across multiple runs (a cursor/date/number boundary, or
an exclusion of already-processed items), or it should be documented plainly that a single run's
`limit` is a hard ceiling on what this workflow can ever label without manual intervention.

## Actual Behavior

No pagination/cursor input exists. `docs/github-label-taxonomy.md`-style priority-label backfill and
content-regex labeling both silently stop being reachable for anything past the newest `limit` items.

## Error Details

```
N/A -- not a crash. Silent under-coverage: a rerun succeeds but makes no further progress.
```

## Visual Evidence

N/A

## Impact

**Severity: Major (functional completeness).** Not blocking merge of PR #328 (these are new,
manually-triggered workflows, not part of an existing live path), but real: the workflows' own stated
purpose — backfilling missing labels across existing issues/PRs — silently fails for any repo with
more matching items than `limit` in a single run.

## Additional Context

A related, narrower issue: neither workflow validates `limit` against GitHub Actions' own 256-job
matrix cap before running. That specific piece was fixed directly in PR #328 (validation added, with
a clear `::error::` message instead of letting GitHub Actions cancel the whole workflow run). This
issue is scoped to the separate, larger gap: even a compliant `limit <= 256` run still can't advance
past its own first result set on a rerun. Implementing a real cursor/exclusion mechanism is a design
decision (which field to page on — issue/PR number, creation date, an explicit "processed" marker) not
attempted in that PR.

## Review Finding Source

- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/328
- **Head SHA at time of finding**: 74acdb2e1d0a2b4b0dd785c2d3b5bb1259230f22
- **Review threads**:
  - https://github.com/AndreHahm/andres-cc-marketplace/pull/328#discussion_r4010612849 (Codex)
  - https://github.com/AndreHahm/andres-cc-marketplace/pull/328#discussion_r4010637359 (CodeRabbit)
- **Reviewers**: chatgpt-codex-connector (Codex), coderabbitai (CodeRabbit) -- raised independently
- **Stated severity**: P2 (Codex); Major (CodeRabbit)
