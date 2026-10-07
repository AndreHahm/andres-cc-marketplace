# Open-Item Format (canonical)

This file is the canonical definition of what a workledger-kit Linear issue looks like. The two master
issues in Linear (`CCM-1` open item, `CCM-2` PR record) are human copy sources that must match it; if
they disagree, this file wins. `scripts/wlgr_open_items.py describe` produces this layout (through
`build_description`) and `classify` reads the first-line key (through `read_dedup_key`).

## Description layout

````text
dedup_key: <owner/repo>|<source-ref>|<fingerprint>

## Summary
...
## Context
...
## Done when
- [ ] ...

## Tracking data
```yaml
schema: 1
github_labels: ["t: bug", "p: high"]
kind: "open-item"
...
```
````

The example is illustrative: the script writes `schema: 1` first and then the remaining keys in
alphabetical order.

- **First line is the dedup key, once.** Linear's `list_issues` truncates long descriptions at roughly
  450-500 characters, so a key at the end of the description is lost in a bulk scan. The key is
  not repeated inside the YAML block, so there is no second copy to drift.
- **The tracking block is one fenced `yaml` block under the fixed `## Tracking data` heading, last in
  the description.** Values are JSON-quoted flat text. Notion rejects a text value that starts with
  `{`, so keep values flat.
- A hand-made issue may have no tracking block and no first-line key. That is not an error: the plugin
  reports it as **drift**, never repairs it silently.

## Dedup key

`<owner/repo>|<source-ref>|<fingerprint>` where the fingerprint is 8 hex characters of SHA-256 over the
whitespace-collapsed, lowercased item text.

| Source | `source-ref` |
|---|---|
| Report | `<repo-relative path>#<ordinal>` among the items extracted from that file |
| GitHub issue | `#<number>` |
| PR record | `PR#<number>` |
| PR follow-up | `PR#<number>/followup#<k>`, or `PR#<number>/followup-cue` for a free-text cue |

Comparison is exact string equality, in code. Linear's text search is fuzzy (a wrong fingerprint still
found the right issue; `#99` matched `#999`), so a search hit is only a **candidate list** to compare,
never proof of identity.

| Outcome | Meaning | Action |
|---|---|---|
| duplicate | existing key equals the candidate key | skip |
| candidate-match | same repo and source ref, different fingerprint | a person confirms; never an automatic merge or update |
| new | no existing key shares repo and ref | propose creation |

An inserted report item shifts later ordinals, which shows up as candidate-matches for a person to
confirm. That is the deliberate, safe failure direction.

## Skipped issues

Skip any issue carrying the label `meta: master` or whose title starts with `[MASTER` in collection,
dedup and views. Masters exist only as copy sources for people.

## Fields the plugin proposes

| Field | Value |
|---|---|
| Status | `Triaged` for imports (collected, not yet human-reviewed). PR records get an explicit status: In Review (open), Done (merged), Canceled (closed unmerged). |
| Labels | `kind: open-item` or `kind: pr-record`; `origin: report`, `github-issue`, `pr-followup` or `pr-backfill`; `type:` and `impact:` mapped from GitHub labels (below). The script proposes these; plugin labels are added by a person (see "Team-scoped labels") |
| Priority | From the GitHub `p:` label (critical = Urgent, high = High, medium = Medium, low = Low); no label for it |
| Relations | `relatedTo` and `blocks` only; never a parent or sub-issue |

Linear's automation owns the four automated status moves (Todo, In Progress, In Review, Ready to
Merge). The plugin records them as evidence and writes only deliberate transitions: Done, Canceled,
reopen. A status that disagrees with the PR's GitHub state is flagged as drift and corrected only with
approval.

## GitHub label mapping

| GitHub label | Linear |
|---|---|
| `t: <x>` | `type: <x>` (`enhancement` becomes `improvement`) |
| `i: <x>` | `impact: <x>` (`minor change` becomes `minor`) |
| `p: <x>` | Linear priority, no label |
| `a:`, `s:`, `auto:` | none (`s: triage` is redundant with `Triaged`) |

Every original GitHub label is also kept in the tracking block's `github_labels` line, so nothing is
lost. `scripts/wlgr_open_items.py annotate` applies this mapping and stores the result in each candidate's
`extra.mapped`.

## Team-scoped labels

Linear label names are unique across the whole workspace, so a team-scoped label cannot reuse a workspace
label's name. The repository's plugin labels are therefore named with the team prefix in lowercase, for
example `ccm plugin: git-kit` for team prefix `CCM`. The workspace-wide labels (`type:`, `impact:`, `kind:`,
`origin:`, `meta: master`) keep their plain names. `onboarding-repositories` lists the labels a repository
needs; a person creates them.

## PR record tracking block

The tracking block for a PR record holds the keys `propose_issue` writes: `kind`, `repo`, `origin`,
`source_ref`, `url`, `state` (`open`, `merged` or `closed`), `merged_at`, `closed_at`, `head_sha` and
`merge_sha`, plus `github_labels` when the candidate has them and `pr` on follow-up items. Referenced issues
and follow-ups are shown in the PR history report, not stored here. The plugin creates a PR record only for a
PR with no linked Linear issue (a Linear identifier in its title, body or branch); a PR linked to an existing
issue stays attached to that issue.
