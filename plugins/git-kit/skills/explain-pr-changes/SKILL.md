---
name: explain-pr-changes
description: >-
  Generate a structured PR changeset summary from the diff between the current branch and origin/main, with an executive summary, optional Mermaid diagrams for complex changes, and a per-changeset NEEDS_REVIEW/APPROVED triage. When updating an already-open PR, also gates on resolving every existing review comment. Use when reviewing, explaining, or writing up what changed in a pull request, updating an existing PR description, or triaging a diff before requesting review.
argument-hint: (optional) issue number to close, e.g. 123
allowed-tools: Bash(git diff:*), Bash(git branch:*), Bash(gh pr:*)
---

# Explain PR Changes

Analyze the diff between the current branch and `origin/main`, and produce a structured, reviewer-focused summary — grouping changes into logical changesets, each triaged as `NEEDS_REVIEW` or `APPROVED`.

**Arguments:** $ARGUMENTS — optionally, an issue number this PR closes.

## Instructions

1. **Check the branch**: make sure you're not on `main`. If you are, this skill has nothing to summarize — stop and say so (don't create a branch on this skill's behalf; that's `commit`'s job).
2. **Gather the diff**: use `git` and `gh` to fetch the diff between `origin/main` and the current branch.
3. If a PR is already open for this branch, you'll be updating it rather than creating a new one — check with `gh pr view` first.
4. **Review comment resolution gate** (only when a PR is already open — skip entirely for a new PR): run `gh pr view --json comments,reviews` to list existing review feedback. If any comments exist, build a resolution table — one row per comment — and classify each as:
   - `FIXED` — the changeset that addresses it (cite the changeset title from step 8)
   - `TRACKED` — a new issue was filed for it (use `github-issue-creator` if one doesn't exist yet; cite the issue number)
   - `SKIPPED` — a one-line justification for not acting on it (e.g. out of scope, already correct, informational-only)

   Every comment must land in exactly one bucket — do not silently omit one from the table. If a comment can't be classified with confidence, ask the user rather than guessing. This table is separate from the changeset triage in step 8 — it accounts for *incoming* feedback, not the PR's own diff.
5. **Holistic analysis**: read the full diff before writing anything. Understand the *intent* behind the changes — the problem being solved or the feature being added — not just the line-level modifications.
6. **High-level summary**: draft a concise executive summary (max 150 words) that gives a reviewer immediate context. This goes at the very top of the output. If an issue number was given as an argument, add "Closes #<number>" to the summary.
7. **Diagrams (optional)**: generate a Mermaid diagram only if the PR introduces or significantly alters a data flow, a call hierarchy, a state machine, or the relationship between new/modified global data structures. Choose the diagram type (`flowchart`, `sequenceDiagram`, `stateDiagram-v2`, etc.) that fits. Keep it focused on what the PR actually touches — don't map the whole application. Give each diagram a one-sentence explanation. Skip this section entirely if nothing warrants a diagram.
8. **Changeset breakdown**: go file by file and group related changes into logical changesets — one or more files that work together toward one part of the PR's goal. For each changeset, produce:
   - A meaningful title (e.g. "Refactor Authentication Logic", "Add User Profile Endpoint")
   - The list of files affected
   - A bulleted summary of the changes — specific enough to call out any change to an exported function's signature, a global data structure, or anything else affecting the external API or public behavior
   - A triage status:
     - `NEEDS_REVIEW` — any modification to logic or functionality: control flow, algorithms, variable assignments, function calls, or public-facing contracts that might affect behavior
     - `APPROVED` — only trivial changes with no logic impact: typo fixes in comments, formatting, renaming a private variable for clarity
     - When in doubt, triage as `NEEDS_REVIEW`
9. **Write the output**: follow `assets/pr-summary-template.md` exactly — same section headers, same structure. No conversational text outside it.
10. **Publish**: use the generated output as the PR body. If a PR is already open for this branch, update its body (and title, if it no longer matches) with `gh pr edit`; otherwise create one with `gh pr create`. If step 4 produced a resolution table, post it as a separate PR comment via `gh pr comment` so reviewers can see how their feedback was handled — don't bury it inside the PR body template.
