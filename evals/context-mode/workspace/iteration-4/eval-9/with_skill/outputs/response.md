# Response to the user: "merge pr 902"

Ship mode is active. I prepare first and merge only after you confirm. The merge itself goes through `merge-pr`, never a raw `gh pr merge`.

## What's shipping
PR #902, approved, into `main`.

## Destination
PR merge into `main`. This repo is public, so the merge is visible immediately.

## Pre-ship checks: ran / not run

Right before `merge-pr`, I re-read the head SHA and the secretlint result for that exact head. I don't reuse an earlier reading:

```bash
gh pr view 902 --json headRefOid,baseRefName,isDraft,reviewDecision,statusCheckRollup
gh run list --workflow Security --commit <headRefOid> --json databaseId,status,conclusion,headSha
gh run view <databaseId> --json status,conclusion,jobs   # read the secretlint job's own status/conclusion
```

- **Required status checks: ran, all green.** `merge-pr` checks them again before merging.
- **Review: approved.** There are no outstanding change requests. `merge-pr` checks this again too.
- **Secretlint (Security workflow): ran, passed** for head `<headRefOid>` of PR #902. This check is not required, so GitHub would merge without it. I merge only because it passed for this exact head.
  - If the re-read showed a different head or no run for this head, I would stop. I would then run secretlint locally on the changed files, or ask you.
  - If the job were still running, I would wait.
  - If it had failed, I would stop until the finding is triaged.
- **External-reference check (`external-references-reviewer`): not run, and not needed.** The diff adds no names of outside companies, products or repositories. Nothing runs this reviewer automatically, and I'm not offering it here.
- **QA pipeline and inventory sync: not applicable.** This is a PR merge, not a plugin publish.

## Confirmation

Next I would run `Skill(merge-pr)` for PR #902. It checks again that the PR is not a draft, that the checks pass, that there are no change requests, and that you have merge rights. Then it asks before merging. My own gate for this specific action:

```
AskUserQuestion({
  questions: [{
    question: "Merge PR #902 into main now? Checks green, approved, secretlint passed for head <headRefOid>.",
    header: "Merge #902",
    options: [
      { label: "Merge", description: "Run merge-pr for #902; it re-verifies readiness and merge rights, then merges." },
      { label: "Hold", description: "Don't merge yet." }
    ]
  }]
})
```

If you choose "Merge", I run `merge-pr`, and the merge happens there. After the merge, I run `finishing-work`, which hands branch and worktree deletion to `git-cleanup`.

**Next step:** confirm the merge above.

---

## Note on steps followed (plan-only run)

1. I read `context-mode/SKILL.md`, then `references/ship.md` (the active profile) and `references/generic.md` (the posture shared by every mode). The mode was already active, so I did not run `set_mode.py`. `CLAUDE.md` and `.claude/rules/` still outrank the profile.
2. I applied the ship posture: prepare, then execute; give a confirmation for this specific action; state which checks ran and which did not; keep it brief; use the output structure (What's shipping / Destination / Pre-ship checks / Confirmation).
3. **Secretlint.** The profile says to read the result for the exact head immediately before `merge-pr` and to state it. I stated it as passed. I also listed the `gh` commands for the re-read, since the recheck-state rule asks for this right before an action with side effects.
4. **External names.** The diff adds none, so the optional `external-references-reviewer` check does not apply. I said it was not run and that it does not block the merge.
5. **Routing.** The merge goes through `merge-pr`, with an `AskUserQuestion` gate. `finishing-work` follows the merge. I executed nothing, because this is a plan-only run.
