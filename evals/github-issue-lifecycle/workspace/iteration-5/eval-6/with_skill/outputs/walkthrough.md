# Walkthrough: Workflow 1, Step 6 (Link to Originating PR) for issue #314

Sources: `plugins/git-kit/skills/github-issue-lifecycle/SKILL.md` and
`plugins/git-kit/skills/github-issue-lifecycle/workflows/create-an-issue.md` (Step 6).
Dry run only. No Bash, git, gh, Skill or Agent call was made.

## Ground rule for both parts

Step 6 says that github-issue-lifecycle **never invokes `collaborating-on-a-pr` itself**. Two reasons:

1. **Cycle.** `create-pr` can invoke this workflow (its Pre-flight step 3.5 files the issues it finds),
   and `collaborating-on-a-pr`'s Path A invokes `create-pr`. If this skill called
   `collaborating-on-a-pr`, the chain `create-pr` -> `github-issue-lifecycle` ->
   `collaborating-on-a-pr` -> `create-pr` would close into a loop.
2. **Path A only links at PR-creation time.** Running it against an issue whose PR is already open
   would make it dispatch `create-pr` and open a second, duplicate PR.

SKILL.md's "When NOT to Use" says the same thing: PR-to-issue linking is `collaborating-on-a-pr`'s job,
and this skill only names that skill as the user's next step. The Quality-gates checklist and the
Reference Guide row ("named to the user as a next step and never invoked") agree.

## Part A: the fix PR has not been opened yet

What I do:

- **No skill invocation.** I do not call `Skill(collaborating-on-a-pr)` or `Skill(create-pr)`.
  I also don't link anything myself: no `Closes #314` edits, no `gh pr` calls. The skill holds no
  `gh pr` grant anyway.
- **Report and route.** I report the filed issue number and name the next step the user takes.

What I tell the user (for example):

> Issue #314 is filed. When you are ready to open the fix PR, open it through
> `collaborating-on-a-pr`, for example by asking "create a PR that closes #314". That skill links the
> issue while it creates the PR, through `create-pr`. I'm not starting it from here, because
> github-issue-lifecycle never invokes `collaborating-on-a-pr`. Doing so could create a
> create-pr / issue-lifecycle loop.

Step 6 is then done, and so is Workflow 1.

## Part B: the fix PR is already open as PR #77

What I do:

- **No skill invocation, and no pointer to `collaborating-on-a-pr`.** Step 6 says plainly: never point
  the user at `collaborating-on-a-pr` for this case. Its Path A would dispatch `create-pr` and open a
  duplicate of PR #77.
- **No direct edit.** This skill can't edit PR #77. It has no `gh pr` grant, and its only `Edit` grant
  covers the session scratchpad (see SKILL.md's Boundaries section). So I don't try
  `gh pr edit 77 ...`, a `gh api .../pulls/77` PATCH, or any similar workaround, and I don't reach for
  another skill to do it either.
- **Ask the user how they want it linked.** The choice belongs to the user, and the options are
  concrete, so I ask through `AskUserQuestion`, not a plain-text question. Example options:
  - "I'll add `Closes #314` to PR #77's description myself" (GitHub then closes #314 when #77 merges).
  - "Link it from PR #77's sidebar (Development section) myself."
  - "Leave it unlinked for now."
  - (The tool's built-in "Other" lets them describe something else.)

What I tell the user (for example):

> Issue #314 is filed. PR #77 is already open, and github-issue-lifecycle can't edit a PR: it has no
> `gh pr` permission. I'm also not sending you to `collaborating-on-a-pr`. Its linking path only works
> while it creates a PR, so it would open a second PR next to #77. How would you like #77 linked to #314?

I then pass on the user's chosen option. This skill takes no further action on PR #77.

## Summary

| Case | Skill invoked | Action | Message to user |
|---|---|---|---|
| A: PR not yet opened | None | Report #314. Don't link anything here | Open the PR through `collaborating-on-a-pr` ("create a PR that closes #314") |
| B: PR #77 already open | None | Don't edit #77. Ask with `AskUserQuestion` | Explain why I can't edit it and why `collaborating-on-a-pr` is the wrong route, then ask how they want it linked |
