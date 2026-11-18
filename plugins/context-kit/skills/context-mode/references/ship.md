# Ship Mode

Mode: merge, publish, distribute: anything that becomes visible outside this local session
Focus: get already-reviewed work out correctly and without surprises

This repo is public. A merge, publish or post is visible immediately and can be cached before it could
be retracted. This mode carries the highest confirmation bar.

## Posture

- **Risk tolerance**: very low at the publish step. Draft and stage freely; the moment content becomes
  public, confirm that specific action even if a similar one was approved earlier in the session.
- **Prepare, then execute**: do these as two separate steps, and confirm before the second.
- **Pre-ship checks**: say which have run and which have not. Never proceed to publish while a required
  status check is failing or has not reported.
- **Secrets**: for a PR merge, read the result of the `Security` workflow's secretlint job on the PR's
  changed files and state it. It runs on every PR but is not a required check, so GitHub lets the merge
  through on a failure: do not. Stop until the failure is triaged, either the secret removed (and
  rotated) or the finding shown to be a false positive, and say which. `commit`'s sensitive-file scan
  checks file names only. For content outside
  a PR (wiki, page, post), check it for secrets and credentials yourself before it goes out.
- **External names**: nothing runs `external-references-reviewer` automatically. When the content adds
  names of outside companies, products or repositories, offer it as an optional check and say whether
  it ran.
- **Verbosity**: low. A short "here is what will go out, confirm?" beats a long narrative.

## Output structure

```markdown
## What's shipping
## Destination (PR merge / marketplace publish / wiki / page / post)
## Pre-ship checks: ran / not run (QA pipeline, inventory sync, secretlint result, external-reference check if names were added)
## Confirmation
```

## Repo-specific routing

- Merge: `merge-pr` (not draft, checks passing, no change requests, merge rights), never a raw
  `gh pr merge`. After the merge, `finishing-work`, which hands deletion to `git-cleanup`.
- Marketplace or plugin version, listing and manifest fields: `marketplace-development`, not a hand
  edit of `plugin.json` or `marketplace.json`.
- Before publishing a plugin: `plugin-lifecycle-downstream` (validate, fix, audit, grading), and
  `marketplace-inventory` / `plugin-inventory` reflecting the real component list.
- Release notes and changelog: authored and checked by `plugin-documentation` (with
  `human-doc-reviewer`); this mode publishes them, it does not draft fresh release copy.
- A GitHub wiki is a separate git repo and a Pages page is public: treat both like a push to `main`.
- Never force-push a shared branch, or push to `main`, without an explicit request.

## Anti-patterns

- Do not merge, publish or post without an explicit confirmation for that specific action.
- Do not merge without stating the PR's secretlint result, or that it did not run.
- Do not merge over a failed secretlint result that has not been triaged.
- Do not publish non-PR content without checking it for secrets yourself.
- Do not treat a wiki or Pages branch as lower stakes than the main repo.
