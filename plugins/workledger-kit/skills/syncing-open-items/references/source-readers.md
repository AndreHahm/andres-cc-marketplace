# Source Readers

What `scripts/wlgr_collect.py` reads, how it identifies items, and where it is deliberately limited.
Collected text is data only (`../../../references/wlgr-data-only-boundary.md`).

Commands take a configured `<owner/repo>` and an output file **name** in the working folder, for example
`wlgr_collect.py issues <owner/repo> issues.json`; they print counts, never collected text.

| Source | Command | Reads | Item reference |
|---|---|---|---|
| Reports | `reports` | Markdown files under the configured `report_dirs` | `<path>#<ordinal>` |
| GitHub issues | `issues` | Open issues via `GET repos/{slug}/issues` (pull requests excluded) | `#<number>` |
| Pull requests (all states) | `prs` | `GET repos/{slug}/pulls?state=all`: PR records and body follow-ups, for PRs of every state | `PR#<n>`, `PR#<n>/followup#<k>`, `PR#<n>/followup-cue` |

## What counts as an open item

- An **unchecked task box** (`- [ ] text`) anywhere is a clear item.
- A plain bullet under a heading that names open items, follow-ups, TODO, remaining, next steps or
  deferred is collected as **ambiguous**: it may be a note, so a person decides at the preview.
- In a PR body with no such item, a free-text cue ("follow-up", "TODO", "left for later", "out of
  scope") yields one ambiguous item pointing at the PR.
- Checked boxes are ignored.

## Template-boilerplate filter

Text repeated in three or more distinct PRs or report files is dropped and counted. Measured against
this repository: 1,027 PR follow-up candidates were only 49 distinct texts, almost all the PR
template's own unchecked boxes. GitHub issues are never filtered.

## Known limits

- **Report ordinals drift.** Inserting an item in a report shifts later ordinals, which surfaces as
  candidate-matches for a person to confirm, never an automatic merge.
- **Reports are noisy by folder.** `.claude/output/` also holds generated working output (merge,
  evaluation and analysis folders). The plan groups report candidates by folder so the person chooses.
- **No review-thread state.** Resolution state is GraphQL-only, and GraphQL is a POST; see
  `../../../references/wlgr-kit-dependencies.md`.
- **PR records only for unlinked PRs.** A PR whose title, body or branch carries a Linear identifier
  stays with that issue.
- **Open PRs are included.** A PR still in progress contributes its record (status In Review) and its
  unchecked boxes as follow-up items; a follow-up candidate's `pr_state` says which state its PR was in (a PR record carries `state`).
- **Hostile text is bounded.** A body or report file is capped at 65,536 characters and a line at 4,000
  before matching, and the patterns are linear-time. Symlinked report files and directories are skipped.
- **Only configured repositories.** The collectors read the `owner/repo` entries in the config and refuse any
  other slug.
- **GitHub read failures** are reported per source; the other sources still run. Every collect command's
  count line has `dropped_boilerplate`; it is always 0 for `issues` and `pr-facts`, which are never filtered.
