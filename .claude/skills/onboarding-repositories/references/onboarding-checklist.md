# Onboarding Checklist

The human steps for onboarding a repository, derived from the setup done for this repository (Linear
team `andres-cc-marketplace`, issue prefix `CCM`). A person does these in Linear and GitHub; the skill
verifies or records an attestation for each.

## Human steps

| # | Step | How it is verified |
|---|---|---|
| 1 | A Linear team exists for the repository, with a short issue prefix | Team and prefix read back through intake's query (once available) |
| 2 | The team's statuses include `Triaged` (imported, not yet reviewed) and `Ready to Merge` alongside Backlog, Todo, In Progress, In Review, Done and Canceled | Statuses read back (once available) |
| 3 | Linear's GitHub integration is connected for the repository, PRs link by the team's identifier prefix, and **automatic issue creation from PRs and GitHub issues is off** | Attested only: settings are not readable through the connector |
| 4 | Linear's automation maps draft PR to Todo, open PR to In Progress, review to In Review, ready to Ready to Merge, and has **no** mapping for merge or close (a person verifies acceptance before Done) | Attested only |
| 5 | Stale auto-close is off; auto-archive is set to its longest period; the parent and sub-issue auto-close settings are understood (this plugin creates flat issues only) | Attested only |
| 6 | A master open-item issue and a master PR-record issue exist in the team, each labelled `meta: master`, with a first-line `dedup_key:` and (open item) a `github_labels` line; both are excluded from saved views | Master issues read back (once available) |
| 7 | `workmanagement-kit`'s configuration maps this repository's `owner/repo` to the Linear team | Open until Wave 3a: the kit's configuration holds one repository and one team today, and the mapping lives there, not in this plugin |
| 8 | Any issue templates that were created are removed; this plugin sets every field itself | Attested only |

A master can serve only its own team (an issue's team cannot change after the first save), so each
repository needs its own pair.

## Label plan

Workspace-wide labels (`type:`, `impact:`, `kind:`, `origin:`, `meta: master`) already exist and are
shared by every team; do not recreate them. Team-scoped labels are the repository's own plugin labels,
named `<team prefix> plugin: <name>` (for example `ccm plugin: git-kit`), one per plugin, and any area
labels the repository wants. The naming rule for team-scoped labels is in
`../../../references/wlgr-open-item-format.md` ("Team-scoped labels"). The skill lists them as: name, scope
(team), reason. A person creates them through `linear-work-management`; this plugin creates no label.

## Config entry

The entry goes in `.claude/workledger-kit.local.json` (untracked). The file's `repos` list **replaces** the
shipped list (which is empty) rather than extending it, so the written list must contain every repository the file should
cover, and any other key already in the file (for example `intake_capabilities`) must be kept:

```json
{ "repos": [ { "slug": "<owner>/<repo>", "report_dirs": [".claude/output"] } ] }
```

The skill shows the complete resulting file for approval before writing it.
