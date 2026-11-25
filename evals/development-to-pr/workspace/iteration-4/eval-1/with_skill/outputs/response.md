# Plan: development-to-pr for ENG-201 (plan-only simulation)

Assumptions (unknown facts, stated and continued):
- The active Linear Issue is ENG-201. Its state is unknown; assume it is In Progress and its branch already exists and is checked out.
- Whether a PR already exists for that branch is unknown. Assume step 2 finds no PR (the "new-PR path"). The user asked for a draft PR, which points to this path.
- The working tree holds in-scope changes. Assume the repository's configured gates can be discovered, but none have run yet.

Step-by-step plan:

1. **Resolve context.** Invoke `Skill(linear-work-management)` to read ENG-201's outcome and title, which will feed the PR summary. Invoke `Skill(linear-github-linking)` to read ENG-201's existing `git-github-evidence` entries. Invoke `Skill(repository-gates)` to read the repository policy profile. No approval needed. Connector use is subject to the host-profile check.
2. **Search for an existing PR before committing.** Use `linear-github-linking` to search by repository, branch, SHA and Linear ID. Assume no PR is found. If a candidate appears instead:
   - `Conflicting` or `Ambiguous`: stop and raise a structured handoff through `AskUserQuestion`. Never pick a candidate silently.
   - `Adoptable`: ask `AskUserQuestion` to confirm identity before treating it as adopted.
   - `Exact`: proceed without extra confirmation.
3. **Step 2.5 is skipped** on the new-PR path. Its cross-model-review gate runs later inside `create-pr`.
4. **Commit.** Invoke `Skill(git-kit:commit)`. It stages, scans for sensitive files, and confirms the message. Its own confirmation gates apply. Tell it explicitly to skip its step 16 (push) and step 17 (Auto-PR), because step 7 owns publication. The commit itself is approved here.
5. **Read back the commit.** Confirm the SHA and branch from `commit`'s output.
6. **Record `commit-linked`.** Append a `git-github-evidence` entry (`stage: "commit-linked"`, `commits: [{sha, recorded_at}]`) through `linear-github-linking`. Before writing, check the known connector limitation: `save_issue` may not accept custom array fields, so use an encoding the connector supports.
7. **Discover the pre-push gate.** Invoke `repository-gates` for discovery only. Carry the gate identity forward to step 12. Nothing is executed here.
8. **Prepare PR metadata.** Write a concise summary from ENG-201's outcome. Add the permitted Linear reference (for example `related-to ENG-201`) and any template content the repository requires. Do not mirror the Issue's full body.
9. **Present and confirm (AskUserQuestion).** Show the repository, branch, commits, destination (base branch), PR metadata, and a draft-state note. Ask for confirmation before publishing. Options: publish as draft, edit metadata, or cancel.
10. **Delegate publication.** On confirmation, invoke `Skill(git-kit:create-pr)` as a draft. Its own pre-flight runs `cross-model-review` against main. Any pre-push git hook fires inside that push. A failing hook stops here.
11. **Read back.** Confirm from `create-pr`'s output the branch, head SHA, PR number and URL, base, and draft state.
12. **Verify no native status change.** Confirm GitHub's Linear integration attached evidence without changing ENG-201's workflow status. If the status changed, report it as drift.
13. **Confirm the gate outcome.** Use `repository-gates` with the gate identity from step 7, bound to the exact head SHA from step 11. Record the real result. Do not assume a pass.
14. **Record `pr-published`.** Append a `git-github-evidence` entry (`stage: "pr-published"`) with the read-back PR identity from step 11. Put the step 13 gate result in `gates[]` exactly as read back, including `pending` or `fail`. Do not create a separate `ci-gates-passed` entry.

Failure handling: if the outcome of a push or PR is unknown, search GitHub by repository, branch, SHA and Linear ID before retrying. Never retry publication blind.

Confirmations: the commit (gated by `git-kit:commit`) and the publication (step 9). Reads and discovery need no approval.

Would record: `commit-linked` (step 6) and `pr-published` (step 14), both via `linear-github-linking`, each with its Transition Contract write.

Would never do: stage, commit or push directly with raw git; run `git add`, `git commit` or `git push` myself; mirror the Issue body into the PR; create a second PR for the same branch; fabricate a `ci-gates-passed` stage; treat a gate as passed without a read-back; move ENG-201's workflow status; use `gh pr edit` or a raw push to update an existing PR (not applicable here, since the path is new-PR); ask the user for a new session.
