# Filing a Pasted Bug Description as a GitHub Issue — What Happens Before Creation

When a user pastes a raw bug description and asks me to file it as a new GitHub issue in this repo, I would not call `gh issue create` immediately. Here is the walkthrough of what should happen first, and why.

## 1. Confirm the target repository

`gh issue create` (or the GitHub API) needs to know which repo to file against. Even though the working directory is this repo's worktree, I would:

- Run `git remote -v` to confirm the origin and figure out the `owner/repo` slug.
- Check that `gh` is authenticated (`gh auth status`) and has access to that repo.
- If the repo has multiple remotes, or the worktree's remote doesn't match what I'd expect, ask the user which repo they mean rather than guessing.

I would not skip this just because "we're already in the repo" — a worktree can point at a fork, a different remote name, or be mid-migration.

## 2. Read the raw bug description carefully before doing anything else

Before drafting anything, I would actually read and understand what was pasted:

- Is this a real bug (unexpected behavior, error, crash) or is it actually a feature request, a question, or a support issue mislabeled as a bug?
- What's the core symptom — what happened vs. what the user expected?
- Is there enough information already present (steps to reproduce, error text, environment, version) or are there obvious gaps?
- Does the paste contain anything that looks like a secret, token, credential, internal URL, or personal data that shouldn't go into a public issue? If so, I would flag it and ask before including it verbatim.

## 3. Check for likely duplicates

Filing a duplicate issue creates noise and can bury an existing thread with more context. Before drafting a new issue I would:

- Search existing issues (`gh issue list --search "<key terms>"` or the GitHub search UI/API) using the most distinctive terms from the bug description (error message, symptom, component name).
- Search closed issues too, in case this was already reported and closed as "won't fix," "duplicate," or fixed-but-regressed.
- If I find a strong candidate match, surface it to the user and ask whether they want to comment on the existing issue instead of opening a new one, rather than deciding that unilaterally.

## 4. Identify what information is missing and ask, don't invent

A raw paste is often incomplete. Common gaps for a bug report:

- Steps to reproduce
- Expected vs. actual behavior
- Environment details (OS, version, branch/commit, relevant config)
- Severity/impact (blocking vs. minor annoyance)
- Whether it's reproducible consistently or intermittent

I would not fabricate any of these to make the issue look more complete. If the paste is missing critical fields, I would either:
- Ask the user directly for the missing pieces, or
- Draft the issue with those fields explicitly marked as "unknown / not provided" rather than guessing plausible-sounding values.

Inventing environment details or reproduction steps that weren't actually given is a real risk here — the guiding principle is "don't assume, state uncertainty."

## 5. Check for a repo issue template or contributing conventions

Before drafting the body, I would look for:

- `.github/ISSUE_TEMPLATE/` (bug report template, form-based `.yml` templates, or a plain `.md` template)
- `CONTRIBUTING.md` for any stated conventions about labels, required sections, or triage process
- Existing recent issues in the repo, to see the house style (heading structure, use of labels, whether maintainers expect a specific format)

If a template exists, I would map the pasted content onto that template's sections rather than inventing my own structure, so the issue is consistent with what maintainers expect.

## 6. Draft the issue — title and body — as a proposal, not a final artifact

I would produce:

- A clear, specific title (not just "bug" or a copy of the first sentence of the paste, but something searchable and scoped).
- A structured body: summary, steps to reproduce, expected behavior, actual behavior, environment, and any relevant logs/error text, formatted in GitHub-flavored markdown.
- Suggested labels (e.g. `bug`) only if I have confidence which labels exist and apply — checking `gh label list` first rather than inventing label names that don't exist in the repo.

## 7. Show the draft to the user before creating anything

This is the key gate. I would present the full drafted title + body back to the user and explicitly ask for confirmation before running any command that actually creates the issue on GitHub — because:

- Issue creation is a public, externally visible, and not-trivially-reversible action (it can be closed/edited but not truly un-created, and it may trigger notifications to watchers/maintainers).
- The user pasted raw, informal notes — my structuring/cleanup pass could unintentionally change the meaning, drop something they considered important, or add something they didn't intend to make public.
- If I found a likely duplicate in step 3, this is also where I'd surface that instead of silently proceeding.

I would not proceed straight from "paste received" to "issue filed" without this checkpoint, even if the request sounded like "just file this as an issue" — a one-line confirmation of the drafted title/body is cheap insurance against filing something wrong or incomplete in a shared, public system of record.

## 8. Only after explicit go-ahead: create the issue

Once the user confirms (or edits and then confirms) the draft, I would run the actual creation command (e.g. `gh issue create --title "..." --body "..." --label "..."`), then report back the resulting issue number/URL so the user has a direct link.

## Summary of the gate sequence

```
1. Confirm target repo/remote + gh auth        -> verify: git remote -v, gh auth status
2. Read & understand the raw bug description    -> verify: symptom, expected/actual, sensitive content check
3. Search for duplicate issues (open + closed)   -> verify: gh issue list --search
4. Identify missing info; ask rather than invent -> verify: explicit gaps listed or user answers received
5. Check for issue template / repo conventions   -> verify: .github/ISSUE_TEMPLATE, CONTRIBUTING.md
6. Draft title + structured body + labels        -> verify: matches template/house style, labels exist
7. Present draft to user for confirmation         -> verify: explicit user approval before any write
8. Create the issue only after approval           -> verify: issue URL returned to user
```

The single most important step is #7: nothing gets written to GitHub until the user has seen and approved the actual drafted content, not just agreed in the abstract to "file this as an issue."
