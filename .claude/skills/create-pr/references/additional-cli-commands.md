# Additional GitHub CLI PR Commands and Template Usage

Extracted from `SKILL.md` to stay under R13's line-budget threshold — reference material, not part of
the numbered Pre-flight Checks / Creating a New Pull Request flow.

## Additional GitHub CLI PR Commands

Here are some additional useful GitHub CLI commands for managing PRs:

```bash
# List your open pull requests
gh pr list --author "@me"

# Check PR status
gh pr status

# View a specific PR
gh pr view <PR-NUMBER>

# Check out a PR branch locally
gh pr checkout <PR-NUMBER>

# Convert a draft PR to ready for review
gh pr ready <PR-NUMBER>

# Add reviewers to a PR
gh pr edit <PR-NUMBER> --add-reviewer username1,username2

# Merge a PR — use the merge-pr skill instead of a raw `gh pr merge` here:
# it checks draft/CI/review status and verifies the caller has merge rights first.
```

## Using Templates for PR Creation

To simplify PR creation with consistent descriptions, you can create a template file:

1. Create the template at an absolute path under the session's scratchpad/temp directory (e.g.
   `<scratchpad-dir>/pr-template.md`) — never a bare relative filename like `pr-template.md`, which
   resolves to the current working directory (often the repo root) rather than a scratch location
2. Use it when creating PRs:

```bash
gh pr create --draft --title "feat(scope): Your title" --body-file <scratchpad-dir>/pr-template.md --base main --assignee <login>
```
