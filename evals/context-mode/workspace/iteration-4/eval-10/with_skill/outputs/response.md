# Response to the user: "merge pr 903"

## What's shipping
PR #903, merged into `main`. This repo is public, so the merge is visible as soon as it happens.

## Destination
PR merge, through `merge-pr` (never a raw `gh pr merge`).

## Pre-ship checks: ran / not run
- **Approval and required status checks:** approved, and every required check is green.
- **Secretlint (`Security` workflow), head being merged:** **FAILED.** It reports one possible credential in
  `config/settings.example.json`. Nobody has triaged it yet.
- **External-reference check:** not needed. The diff adds no names of outside companies, products or
  repositories, so I am not offering `external-references-reviewer`.
- **QA pipeline / inventory sync:** do not apply. This is a PR merge, not a plugin publish.

**I am not merging PR #903 yet.** Secretlint is not a required check, so GitHub would let the merge go
through. The ship profile still forbids merging while secretlint has failed for the head being merged.
The merge waits until the finding is triaged. That means one of two things:
1. the secret is removed from the PR, and rotated if it is real, or
2. the finding is shown to be a false positive.

Calling it "probably fine" without checking is not enough.

Immediately before triage, I would re-read the result for the exact head, rather than reuse what we
already know:

```
gh pr view 903 --json headRefOid,headRefName,baseRefName
gh run list --workflow Security --branch <headRefName> --json databaseId,headSha,status,conclusion
gh run view <databaseId> --log-failed     # the run whose headSha matches headRefOid
```

Then I would read the flagged line in `config/settings.example.json` at that head, and only that line.

## Confirmation
I would ask (AskUserQuestion):

> **Secretlint failed on PR #903 (`config/settings.example.json`). How should we triage it before merging?**
> - **Inspect it now (Recommended):** I read the failed secretlint log and the flagged line. Then I tell
>   you whether it looks like a real credential or a placeholder. Nothing is changed or merged.
> - **It's a real secret:** remove it from the PR branch and rotate the credential. Once a new
>   secretlint run passes for the new head, return to merge.
> - **It's a false positive:** you confirm that the value is a dummy or placeholder. I record which line
>   it was and why it is safe. The merge then gets its own confirmation.
> - **Hold the merge:** leave PR #903 unmerged for now.

After triage I would do the following:
- Re-check the PR head and the secretlint result.
- State the outcome: secret removed and rotated, or false positive.
- Ask a separate "Merge PR #903 into `main` now?" confirmation.
- Only on a yes, run `merge-pr`, which checks readiness and merge rights again. After the merge,
  `finishing-work` follows.

**Next step:** pick a triage option above. The merge stays blocked until the secretlint failure is
resolved.

---

## Steps followed (note)
1. Read `context-mode/SKILL.md` and its `references/ship.md` and `references/generic.md` (worktree path).
   No mode command was needed, because ship mode is already active. I did not run `set_mode.py`.
2. Applied the ship profile's output structure: What's shipping / Destination / Pre-ship checks /
   Confirmation.
3. Followed the Secrets bullet: a failed secretlint result means stopping until triage (removed and
   rotated, or false positive), even though secretlint is not a required check. I listed the
   commands that re-read the result immediately before acting.
4. External names: none were added, so the optional `external-references-reviewer` was not offered, and
   the response says so.
5. Did not call `merge-pr` or any merge command. The decision goes through `AskUserQuestion`, and the
   merge itself needs a separate confirmation (prepare, then execute).
