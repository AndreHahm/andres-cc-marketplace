# Baseline Dry Run: `/create-pr 123`

Context: invoked as a direct top-level command, no delegating skill. Branch `feat/example-widget`.
Everything is already committed and pushed. No PR is open yet. Issue #123 should be closed by this PR.

No specialized skill/methodology is used here — this is standard git/gh knowledge only.

---

## Step 1 — Confirm current branch and clean state

```
git status
git branch --show-current
```

Purpose: verify I'm actually on `feat/example-widget` and that the working tree is clean (no
uncommitted changes) before doing anything else. The task states everything is already committed
and pushed, but I'd still confirm this rather than assume it, since creating a PR from a dirty or
unpushed branch produces a PR that doesn't reflect the intended diff.

Expected output: clean tree, current branch `feat/example-widget`.

## Step 2 — Confirm the branch is pushed and up to date with its remote

```
git fetch origin
git log origin/feat/example-widget..feat/example-widget
git log feat/example-widget..origin/feat/example-widget
```

Purpose: confirm local and remote are in sync (no unpushed local commits, no unpulled remote
commits). If there were unpushed commits I'd run `git push` (or `git push -u origin
feat/example-widget` if no upstream is set) before opening the PR — a PR opened against a stale
remote branch would be missing commits.

## Step 3 — Confirm no PR already exists for this branch

```
gh pr list --head feat/example-widget --state all
```

Purpose: avoid creating a duplicate PR. The task states no PR is open yet, but I'd still check
before calling `gh pr create`, since `gh pr create` will error out (or, in some edge cases,
silently reuse) if one already exists.

## Step 4 — Look up issue #123 to ground the PR title/body

```
gh issue view 123
```

Purpose: read the issue's actual title and description so the PR title and body accurately reflect
what's being fixed/implemented, rather than guessing from the branch name alone. Not strictly
required to make the closing keyword work (that only needs the issue number), but useful for
writing an accurate PR description.

## Step 5 — Review the diff and commit history that will make up the PR

```
git log main..feat/example-widget --oneline
git diff main...feat/example-widget --stat
```

Purpose: build an accurate summary of what changed, for the PR body's "Summary" section, and to
sanity-check that the branch's diff is what's expected (nothing unrelated snuck in).

## Step 6 — Determine the base branch

```
gh repo view --json defaultBranchRef -q .defaultBranchRef.name
```

Purpose: confirm the repo's default branch (assumed `main` per repo context) so `gh pr create`
targets the right base explicitly rather than relying on an assumed default.

## Step 7 — Create the PR with `gh pr create`, embedding the closing keyword in the body

This is the step that actually produces "PR closes issue #123." No other tool, skill, or delegated
call is involved in a baseline flow — GitHub's own issue-linking behavior is triggered purely by
specific keyword text in the **PR body** (or a commit message on the PR's commits), not by any
separate API call. The keywords GitHub recognizes: `close`, `closes`, `closed`, `fix`, `fixes`,
`fixed`, `resolve`, `resolves`, `resolved`, followed by `#123` (or the full owner/repo#123 form).

I would run:

```
gh pr create \
  --base main \
  --head feat/example-widget \
  --title "<derived from commits/issue, e.g. 'Add example widget'>" \
  --body "$(cat <<'EOF'
## Summary
<1-3 bullet points summarizing the change, derived from Step 5's diff/log>

Closes #123

## Test plan
<checklist derived from what the diff touches>
EOF
)"
```

Key details:
- The body is passed via a heredoc (not a `--body-file` unless a longer body warrants one) to
  preserve formatting exactly, avoiding shell-escaping mistakes that could corrupt the `Closes #123`
  line.
- `Closes #123` is placed on its own line, which is the safest form — GitHub's auto-link parser is
  reliable with the keyword directly adjacent to a bare `#123` reference and not embedded inside a
  larger sentence that might get mangled by markdown rendering.
- I would NOT rely on the branch name or a separate `gh issue` linking call to create this
  connection — GitHub does not auto-link issues from branch names or commit content alone; it
  specifically requires the closing keyword to appear in the merging PR's description (or in a
  commit that's part of the PR, but putting it in the PR body is the standard, most visible
  approach and the one I'd use here).
- If this were going through a delegated flow (e.g., a separate "linking" step), the exact
  instruction I'd give it would be: *"Include the line `Closes #123` as its own line in the PR
  body, verbatim, using the bare issue number (not an owner/repo qualifier, since this is the same
  repo)."* In this baseline flow there is no such delegation — `gh pr create`'s `--body` argument is
  the single point where this needs to land correctly.

## Step 8 — Confirm the PR was created and that the closing line actually landed

```
gh pr view feat/example-widget --json number,url,body,closingIssuesReferences
```

Purpose / verification method:
1. `--json body` — re-read the PR body as GitHub actually stored it, and grep/eyeball it for the
   literal `Closes #123` line, confirming the text wasn't mangled by shell quoting or markdown
   escaping on the way in.
2. `--json closingIssuesReferences` — this is the authoritative check, not just "the text is
   present." GitHub's GraphQL/REST layer parses the body for closing keywords and exposes the
   *actual resulting linkage* as structured data (an array of issues that will be closed on merge).
   I would confirm issue #123 appears in that array with its number matching — this proves GitHub's
   parser actually recognized the keyword, not just that the string exists in the body (e.g. a typo
   like "Closess #123" or "Closes # 123" would show the text but fail to produce a real link, and
   `closingIssuesReferences` is what catches that).
3. As a redundant human-visible check, `gh pr view feat/example-widget --web` or the printed PR URL
   itself renders a "Closes #123" cross-link in the GitHub UI with issue #123's title, one green
   checkmark, and (after merge) an automatic close — but since this is a dry run, no such UI
   fetch/verification actually happens beyond describing the check.

If `closingIssuesReferences` came back empty despite the body containing what looks like the right
text, the fix would be to `gh pr edit <number> --body "<corrected body>"` and re-check, since a
malformed keyword or number reference is the most common cause of the link silently not forming.

## Step 9 — Report result

Report the PR URL, its number, confirm draft-vs-ready state (ready, since no draft flag was
requested), and explicitly state that issue #123 is linked to close on merge, based on the Step 8
verification.

---

## Summary of what makes "Closes #123" actually work

- No separate API call or delegated skill is needed — it is entirely a function of the **text
  GitHub parses out of the PR body** (or a commit on the PR) at creation/edit time.
- The single point of failure is the exact text passed to `gh pr create --body` (or a later `gh pr
  edit --body`): it must contain a supported keyword (`Closes`, `Fixes`, `Resolves`, or their
  inflections) immediately followed by a bare `#123` for the same repository.
- The only reliable verification is not "the string is present in the body" but `gh pr view --json
  closingIssuesReferences`, which reflects GitHub's own parse of that text into a real linkage —
  that's the check I'd run before reporting success.
