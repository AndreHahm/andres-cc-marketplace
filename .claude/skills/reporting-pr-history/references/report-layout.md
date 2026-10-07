# PR History Report Layout

Produced by `scripts/wlgr_pr_report.py`; this file documents what it emits so a reader can check it.

## Header

Title `PR history (baseline|delta since <date>): <owner/repo>`, the generation date, the PR count, and a note
that the report is a dated snapshot and shows explicit references only.

## Sections

| Section | Content | Rule |
|---|---|---|
| Timeline | Date, PR, state (merged, closed, open), title | Sorted by merge or close date, then PR number. An open PR has no date, is shown as `-` and sorts first. A delta lists every open PR plus PRs merged or closed on or after the date |
| PR to referenced issues and items | Per PR: `closes`, `follow-up/continues`, `mentions` | Explicit references in the title and body only; each number in one group; a PR never references itself |
| Issues closed by merged PRs | Issue number and the merged PR(s) that closed it | Closing keywords in a **merged** PR only; a closed-unmerged PR closes nothing |
| Follow-up PRs and tasks | PRs with an explicit follow-up/continues reference or unchecked task boxes | A box whose text repeats in three or more PRs is the PR template and is not counted; repetition is judged over all PRs, so a delta agrees with the baseline |
| Per plugin (from the PR title scope) | PR count and PRs with follow-ups per plugin | The plugin is the title's conventional-commit scope (`feat(git-kit): ...`); `feat(a,b)` counts the PR under both `a` and `b`; no scope counts as `(no scope)`; a `\|` in a scope is replaced by `/` |

## Reference forms

Matching is case-insensitive.

- `closes`: `close`, `closes`, `closed`, `fix`, `fixes`, `fixed`, `resolve`, `resolves` or `resolved`,
  then blanks (optionally a colon) and `#N`. Other forms (`closing`, `fixing`) are not matched.
- `follow-up/continues`: `follow-up to|of|for`, `follow-ups to|of|for`, `continues`, `builds on`,
  `supersedes` or `part of`, then `#N`. This is the **explicit-reference** meaning; the collectors' free-text
  "follow-up cue" is a different, ambiguous signal used for open items, not here.
- `mentions`: any other bare `#N` not part of a longer word or path.

A `#N` can name an issue or a PR; GitHub shares the number space, so the report does not say which.

## What the report does not contain

- **Inferred links.** They need the classification capability; when available they are marked inferred, with
  their evidence, and never presented as fact.
- **Review-thread state**, **Linear status** and **archived Linear items**: it reads GitHub only.

## Notion size handling

Each text block or property is at most 2,000 characters (see `../../../references/wlgr-kit-dependencies.md`).
Chunk with `wlgr_open_items.py chunk <report.md> <chunks.json>`; the chunker prefers paragraph, then line boundaries, and
splits only an over-long single line. Intake has no field for chunked page content yet, so the chunks stay
in the working folder until it does.
