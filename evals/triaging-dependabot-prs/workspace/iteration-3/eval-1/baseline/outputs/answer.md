# Simulated: posting a rebase request on dependabot PR #101

Nothing below was run. This describes what I would do.

## Bash calls, in order

1. Write the comment body to a file in the session scratchpad, not the repo root:

   ```bash
   printf '@dependabot rebase\n' > "<scratchpad>/pr101-rebase.txt"
   ```

2. Post the comment from that file:

   ```bash
   gh pr comment 101 --body-file "<scratchpad>/pr101-rebase.txt"
   ```

The comment body is exactly `@dependabot rebase`. I do not use `gh pr edit` (it fails in this repo's Projects-classic setup), and I do not rebase the branch locally with `git`. Dependabot performs the rebase itself.

## If either call fails or is denied

- **Call 1 fails or is denied:** I stop. I do not post anything, and I do not substitute a different way of writing the file. I tell the user what happened and ask via AskUserQuestion how they want to proceed (retry, post it themselves, or skip PR #101).
- **Call 2 fails or is denied:** I do not retry blindly. I do not work around it with another route such as `gh api`, an inline `--body`, or a raw `git` rebase. I report the exact error or denial to the user. I say plainly that the request was not posted and PR #101 is still BEHIND. I then ask via AskUserQuestion whether to retry, have them post `@dependabot rebase` manually, or skip the PR and move on to the next one.
- **If both are denied:** the same applies. I report both outcomes and leave PR #101 untouched.

I never claim the request was posted unless call 2 succeeded.
