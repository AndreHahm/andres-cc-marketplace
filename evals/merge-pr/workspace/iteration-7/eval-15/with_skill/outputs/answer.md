# Merge-PR Fork PR Readiness Check: mergeStateStatus = BEHIND

## Answer

**Does this check block readiness?** YES

The `BEHIND` status from `mergeStateStatus` is a **blocking gate**. The PR is not ready to merge.

## What to tell the user

Since this is a cross-repository PR (fork), we cannot apply `/sync-branch` locally. Instead, direct the message to the **contributor**:

> "The pull request branch is behind the base branch (`<baseRefName>`) according to GitHub's merge status. The contributor must update their branch before this PR can be merged. They should sync their fork branch with the base branch using their local git tools or GitHub's UI."

## Reasoning

Per the skill instructions:

- For fork PRs (`isCrossRepository` = `true`), we use `mergeStateStatus` from GitHub instead of running a local compare API call
- If `mergeStateStatus` is `BEHIND`, we must **stop and block the merge**
- **Do NOT** point at `/sync-branch` — the skill explicitly states: *"this skill has no local git access to push to a fork's branch, so `/sync-branch` doesn't apply here the way it does for a same-repository PR"*
- The responsibility to update the branch lies with the **contributor who owns the fork**, not with the reviewer running this skill

## Merge readiness result

**BLOCKED** — Readiness check failed at "Not behind base". Do not proceed to other readiness checks or merge.
