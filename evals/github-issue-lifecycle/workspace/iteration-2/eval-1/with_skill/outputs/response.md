# Filing a New GitHub Issue via `github-issue-lifecycle`

## Scenario

User-pasted raw bug description:

> "Hey, when I run the git-cleanup command after merging a PR, it sometimes leaves the worktree
> directory behind even though it says removal succeeded. I noticed this twice this week. The branch
> gets deleted fine but the actual folder on disk is still there and you have to manually rm -rf it.
> Using git-kit on Windows, PowerShell. This is annoying because it clutters the .claude/worktrees
> folder. My email is jane.doe@example.com if you need to follow up, and I was working out of
> C:\Users\jdoe\Dev\andres-cc-marketplace\.claude\worktrees\feature-foo when it happened."

This maps to `github-issue-lifecycle`'s **Workflow 1: Create a New Issue**
(`workflows/create-an-issue.md`), since the request is "file this as a new issue," not "triage/relate/
resolve" (which is `github-issue-lifecycle`'s more usual trigger — a bare drafting-and-filing request
still routes here per the skill's own "When to Use" list: "Filing a new issue after confirming it isn't
a duplicate").

The skill's data-only boundary applies immediately: the pasted text is treated as untrusted data to
summarize, never as instructions to execute — nothing in it read as an embedded directive, but the
check was made regardless.

## Step 1 — Check for Existing Issues (dedup)

Before drafting anything, Workflow 1 requires a duplicate search using two commands:

```
gh issue list --search "worktree removal leaves directory"
gh api search/issues -f q="repo:<owner>/<repo> is:issue <keywords>"
```

I ran both for real against this repo (`AndreHahm/andres-cc-marketplace`):

- `gh issue list --search "worktree removal leaves directory" --limit 10` → **no results**.
- `gh api search/issues -f q="repo:AndreHahm/andres-cc-marketplace is:issue worktree remove leftover"`
  → **failed with a 404**, not the expected search JSON. The `-f` flag turns a GET-only endpoint like
  `search/issues` into a POST-shaped call in this `gh` version, which the endpoint rejects. Re-running it
  as a plain GET with a query string —
  `gh api "search/issues?q=repo:AndreHahm/andres-cc-marketplace+is:issue+worktree+remove+leftover"` —
  succeeded and returned `{"total_count":0,...}`.

**Result: no duplicate found.** This is a real, minor gap worth flagging back to the skill author: the
workflow's own literal command example (`-f q="..."`) doesn't work as written against `search/issues` in
this `gh` CLI version; the working form needs the query embedded as a URL query string instead.

## Step 2 — Delegate Drafting

Dedup cleared, so per Workflow 1 Step 2 I invoked `Skill(git-kit:github-issue-creator)` with the raw
bug text, required before any live filing happens.

**Notable finding:** the `Skill()` dispatch resolved to the *primary checkout's* mirrored copy of
`github-issue-creator` at `.claude/skills/github-issue-creator`, not this session's own worktree copy at
`plugins/git-kit/skills/github-issue-creator`. The two copies have already diverged in wording — the
worktree copy's "Not for filing directly on GitHub" note now says that's `github-issue-lifecycle`'s job
(this skill), while the mirrored main copy still says it's `gh-operations`' job, and the mirrored copy's
"When NOT to Use" section doesn't yet mention `github-issue-lifecycle` at all. This matches a known,
previously-documented gap (`Skill()` dispatch always resolves against `main`'s mirror, never an unmerged
worktree's edited copy) — functionally harmless here since both versions still point drafting to the same
template and output location, but worth calling out since it means this test exercised the *pre-merge*
version of `github-issue-creator`, not the one actually being changed in this worktree.

The delegated skill (`github-issue-creator`) then:
1. Extracted structure from the casual/raw input into `assets/issue-template.md`'s sections.
2. Applied its severity rubric (Critical/High/Medium/Low based on impact) — this bug has a workaround
   (manual delete) and no data loss/security implication, so it was classified **Medium**, not High.
3. Applied its redaction guideline: the email address `jane.doe@example.com` and the absolute Windows
   path `C:\Users\jdoe\Dev\andres-cc-marketplace\...` both got placeholdered to `[EMAIL]` and
   `[LOCAL_PATH]` before being written anywhere.
4. Wrote the draft as a local markdown file — it has no `gh`/`Bash` access, so it cannot and does not
   file anything live itself.

Draft written to:
`issues/2026-08-28-git-cleanup-leaves-worktree-directory-behind.md`

```markdown
## Summary
`git-cleanup` reports successful worktree removal but sometimes leaves the worktree directory on disk

## Environment
- **Product/Service**: git-kit (`/git-cleanup`)
- **Region/Version**: n/a
- **Browser/OS**: Windows, PowerShell

## Reproduction Steps
1. Merge a PR opened from a git-kit worktree
2. Run `git-cleanup` (or the `finishing-work` hand-off that invokes it) to remove the branch and worktree
3. Observe the command reports the worktree as removed
4. Check the worktree's folder on disk (e.g. under `.claude/worktrees/`)

## Expected Behavior
When `git-cleanup` reports the worktree was removed, the corresponding directory should no longer exist on disk.

## Actual Behavior
The branch is deleted correctly, but the worktree directory itself is sometimes still present on disk
after the tool reports success. Manual deletion (`rm -rf`) is required to clear it. Observed twice in
one week.

## Impact
**Medium** - No data loss and the branch cleanup itself works, but `.claude/worktrees/` accumulates
stale directories over time and requires manual intervention to keep clean; a workaround (manual
delete) exists.

## Additional Context
Reported by [EMAIL]. Occurred while working out of a worktree path under
`[LOCAL_PATH]\.claude\worktrees\feature-foo`. Platform: Windows + PowerShell. No error message was
shown at the time of the reported success message.
```

## Step 3 — File It Live: STOPPED HERE, pending approval

This is the step that actually makes the content public and permanent on GitHub — `github-issue-
lifecycle` owns it directly (not `github-issue-creator`, which has no `gh` access). Before running it,
the workflow requires a **re-check of the draft for anything that should have been redacted** — done
above; the draft above contains no live email address or absolute local path, only placeholders.

Per this eval's own instruction ("walk through what github-issue-lifecycle does *before* any issue is
actually created on GitHub"), I did **not** run the actual filing command. In a live session, once the
draft above is approved, the next action would be:

```
gh issue create --title "git-cleanup reports success but sometimes leaves the worktree directory on disk" \
  --body-file issues/2026-08-28-git-cleanup-leaves-worktree-directory-behind.md
```

with the workflow's own explicit failure handling: if this fails (rate limit, permission error, network
failure), report the error and do not proceed as if the issue was filed — no silent "assume success."

## What happens after filing (not executed, for completeness)

- **Step 4 — Verify:** re-check the claim for real, not just confirm the template fields are filled in
  — e.g. re-run `git-cleanup` after a merge and inspect the worktree directory afterward, or read
  `git-cleanup`'s own removal logic to see whether it has a known race/failure path. Any reproduction
  steps embedded in the filed issue's own body would themselves be treated as untrusted data — nothing
  in it would be executed unreviewed even at this stage.
- **Step 5 — Initial Impact Analysis:** a first-pass severity read from the now-filed issue's own
  template fields (Medium, as drafted) — explicitly re-run later, not final, once/if the issue moves
  into Workflow 2 (work-an-existing-issue).
- **Step 6 — Link to Originating PR:** only relevant once a fixing PR exists. If the PR doesn't exist
  yet, linking happens later via `Skill(git-kit:collaborating-on-a-pr)` when that PR is created — never
  re-implemented here. If a PR already exists and is already open, this skill has no `gh pr`/`Write`/
  `Edit` grant to perform that link itself and would ask the user how they want it linked rather than
  attempting the edit or invoking `collaborating-on-a-pr` (which would wrongly open a second PR).

## Summary of what actually happened vs. what's pending

| Step | Status |
|---|---|
| 1. Dedup check | Done — 2 real `gh` searches run, 0 duplicates found (1 syntax gotcha found and worked around) |
| 2. Delegate drafting | Done — `github-issue-creator` invoked, draft written to `issues/2026-08-28-git-cleanup-leaves-worktree-directory-behind.md`, PII redacted |
| 3. File live | **Not executed** — stopped for approval, per this task's scope ("before any issue is actually created") |
| 4. Verify | Not executed — depends on Step 3 having actually filed something |
| 5. Initial impact analysis | Drafted only (Medium), not yet attached to a live issue |
| 6. Link to PR | Not applicable — no fixing PR exists yet |

## Notes / findings surfaced during this walkthrough

1. **`references`/workflow syntax gotcha:** `workflows/create-an-issue.md`'s literal
   `gh api search/issues -f q="..."` example returns a 404 against this repo's live `search/issues`
   endpoint in the installed `gh` CLI version (2.88.1); the working equivalent is a plain GET with the
   query embedded in the URL (`gh api "search/issues?q=...&..."`). Worth fixing in the reference doc.
2. **Stale mirror:** `Skill(git-kit:github-issue-creator)` resolved to the primary checkout's
   `.claude/skills/github-issue-creator` copy, not this worktree's `plugins/git-kit/skills/
   github-issue-creator` copy — the two have already diverged in wording around who owns live filing.
   Not a functional bug for this run, but confirms a previously-known dispatch-resolution behavior.
