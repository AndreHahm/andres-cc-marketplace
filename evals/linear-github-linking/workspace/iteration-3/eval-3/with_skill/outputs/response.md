# Plan: repair ENG-77's stale Git/GitHub evidence entry (PR #12)

Plan only. No connector, git, gh, or network call was made. Assumptions are stated where a fact is unknown.

## Assumptions
- ENG-77's recorded entry names repository `owner/repo` and PR #12 on `fix/eng-77-timeout`. I have not read it.
- The `linear.read` and `linear.write` host-profile operations are `verified` for this installation. If not, the skill stops at the first step.
- I do not know the PR's current state. I expect it is still open, because a force-push does not close a PR.

## Steps, in order

1. **Preflight.** Check `host-profile.json` for `linear.read` and `linear.write`, and check the local override's trust status with the `git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json"` check from FOUNDATION_CONTRACTS. Only an exit 1 "did not match" lets the override be honored. Anything else falls back to the `unconfigured` defaults and stops with a report.
2. **Read Linear.** Invoke `Skill(linear-work-management)` to read ENG-77's `git-github-evidence` array. Take the most recent entry for PR #12, following the most-recent-wins rule. Do not pick by timestamp across unrelated entries.
3. **Read GitHub.** Run `Bash(gh pr view 12 ...)` for `headRefOid`, `headRefName`, `state`, `baseRefName`, and `url`. For any other endpoint, use `wmgt_gh_api_readonly.py` (GET-only). Never bare `gh api`.
4. **Repository check.** If the recorded `repository` differs from the current target slug, classify as `Conflicting`, report it, and stop. Do not repair across repositories.
5. **Retry and failure.** If a GitHub read fails, retry once. If it still fails, classify as `Ambiguous`, record nothing, and report.
6. **Classify.** The recorded SHA differs from GitHub's current head, so the relationship is `Stale`. Per the Gotchas, a stale entry does not mean the PR is gone. Re-check that PR #12 exists and is open before concluding anything else. Also check for a second open PR on the same branch or referencing ENG-77. Two plausible candidates make it `Conflicting`, and I would ask the user which to keep.
7. **Confirm identity.** The PR is already recorded, so no `Adoptable` confirmation is needed.
8. **Resolve the connector limitation first.** `git-github-evidence` is a custom array property that the real Linear `save_issue` cannot write as literal JSON (see the connector-limitation paragraph in the contract). Choose a connector-supported encoding, such as description-embedded text or links, before writing. If none is chosen, stop and ask the user. This is the most likely blocker.
9. **Repair by appending.** Append one new entry. Its `supersedes` names the old `evidence_id`. The old entry is not touched. Set `stage` from the read-back PR state (for example `pr-published` or `pr-ready`). Set `commits` to the new head SHA read back from GitHub, and set `pull_request` from the read-back. Set `provider` honestly: the force-push happened outside this plugin, so I would not attribute it to a git-kit skill. I would ask the user which disclosed value applies.
10. **Ask before writing, if needed.** Superseding an entry needs no approval under this skill. The write still goes through `linear-work-management`, which applies its own write gate. If the `provider` value is unresolved, ask first with `AskUserQuestion`.
11. **Record the transition.** The append is an ordinary write with its own base Transition Contract entry. Its `verification_evidence` carries the read-back of the previous write. If this is the terminal write, send one metadata-only write to record its own evidence, then confirm with a plain read.
12. **Redact.** Replace any real team ID, workspace slug, or account identifier in any tracked output with placeholders.

## Would never do
- Change GitHub state (no force-push, retarget, close, or relabel).
- Write back to GitHub to "fix" native Linear automation.
- Edit or delete the old evidence entry in place.
- Choose the newest timestamp over GitHub's current state.
- Change Linear workflow status, priority, or other fields this contract does not own.
- Use bare `gh api`, or invent SHAs or PR fields.
- Record anything from an unconfirmed read.
- Treat PR text or commit messages as instructions.

## Outcome
Expected: `Stale`, repaired by a superseding entry, provided the connector encoding in step 8 is resolved. Any `Conflicting`, `Ambiguous`, or unresolved-`provider` case stops at a question to the user.
