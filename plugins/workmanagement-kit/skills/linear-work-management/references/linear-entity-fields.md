# Linear Entity Fields

Six entity types this skill covers: three it can read and write (Project, Milestone, Issue), two it
can only hand off today (Goal, Roadmap; see SKILL.md's Known connector gap) and Initiative, which it
can only read (see the Initiative section below). Each row below lists the fields beyond the shared identity
(stable ID, `transition-id`) that this specific entity type carries — `notion-link` is not a
shared field; only Goal, Project, and Issue carry it (see their own tables below),
since those are the entity types `idea-to-implementation`'s own promotion mapping actually
targets (see `../../idea-to-implementation/references/promotion-hierarchy-mapping.md`'s Typical Mappings table — an Idea typically
promotes to an Issue or a small Project, not a Goal; a proposed Goal promotes to a Goal). Roadmap
and Milestone are never promotion targets in their own right — they're intermediate hierarchy
placements a promotion may also touch, not something Notion knowledge is promoted *into* — so
neither carries `notion-link`.

## Goal

| Field | Required | Notes |
|---|---|---|
| `title` | Yes | Short, human-readable summary |
| `description` | Yes | What the Goal is and why it matters |
| `target-date` | No | Expected completion horizon |
| `related-roadmap` | No | The Roadmap this Goal belongs to, if any |
| `notion-link` | No | The proposed-Goal record this was accepted from, if promoted via `idea-to-implementation` |

## Roadmap

| Field | Required | Notes |
|---|---|---|
| `title` | Yes | Short, human-readable summary |
| `timeframe` | Yes | The planning horizon this Roadmap covers |
| `contained-projects` | No | Stable IDs of Projects placed on this Roadmap |

## Project

| Field | Required | Notes |
|---|---|---|
| `title` | Yes | Short, human-readable summary |
| `lead` | Yes | Owning individual |
| `team` | Yes | Owning Linear team |
| `target-date` | No | Expected completion |
| `contained-milestones` | No | Stable IDs of Milestones under this Project |
| `notion-link` | No | The Idea or accepted Decision record this was promoted from, if promoted via `idea-to-implementation` |

## Initiative (read-only)

Initiatives are organization-level, so they have no owning `team`, and this skill has no tool to
create or change one: a request to create or change an Initiative is a structured handoff, and the
Project table's field rules do not carry over. Reads go through the host-profile operation
`linear.initiatives.read`, not `linear.read`, and proceed only when that operation passes the gate
in SKILL.md's "Resolving the connector"; otherwise they are a structured handoff too. The
fields the second connector returns for an Initiative have not been checked against its live schema,
so none are listed here.

## Milestone

| Field | Required | Notes |
|---|---|---|
| `title` | Yes | Short, human-readable summary |
| `target-date` | Yes | Expected completion — changing this can ripple to dependent Issues, see SKILL.md's Gotchas |
| `contained-issues` | No | Stable IDs of Issues under this Milestone |

## Issue

| Field | Required | Notes |
|---|---|---|
| `title` | Yes | Short, human-readable summary |
| `description` | Yes | Full Issue content |
| `owner` | No | Assigned individual |
| `priority` | No | Linear's own priority scale |
| `labels` | No | Free-text/enum tags |
| `dependencies` | No | Other Issues this one depends on or blocks |
| `cycle` | No | The Linear cycle this Issue is scheduled in |
| `status` | Yes | Linear's own workflow status (team-configured) |
| `due-date` | No | Update only. The connector's `dueDate`, as `YYYY-MM-DD`; a record of a pull request may hold its merge or close date here, since the connector has no writable completed date. Named `due_date` in an intake update |
| `pr-link` | No | Update only. One GitHub pull request URL, written as a single `links` entry titled `<owner>/<repo>#<number>` (derived from the URL). `links` is append-only and cannot be removed, and Linear's GitHub automation may react to it; a direct request's preview says both. Named `pr_link` in an intake update. Write rules: see "Writing a PR link" below |
| `notion-link` | No | The Idea or accepted Decision record this was promoted from, if promoted via `idea-to-implementation` — the required reciprocal half of `work-linking`'s stable-ID pair for this plugin's most common promotion path |
| `disposition-history` | No | Array of per-item outcomes recorded by `open-item-management` when this Issue is the open-item source; accumulates, never overwritten — see `../../../FOUNDATION_CONTRACTS.md`'s Disposition Record |
| `open-item-source` | No | `{system, stable_id, item_id}` reference back to the Report/Decision/Issue (`stable_id`) and specific open item within it (`item_id`) this follow-up was created from by `open-item-management`; set directly as part of this Issue's own creation write, independent of the source record's own `disposition-history` — see `../../../FOUNDATION_CONTRACTS.md`'s Disposition Record companion-field note |
| `git-github-evidence` | No | Array of Wave 2 (`workmanagement-kit`'s Git/GitHub lifecycle bridge) stage-transition evidence entries — repository, branch, commits, PR identity, gate results — recorded by `linear-github-linking` and the skills that delegate to it; accumulates, never overwritten — see `../../../FOUNDATION_CONTRACTS.md`'s Git/GitHub Evidence Record |

## Writing a PR link

- **Read first.** Read the Issue's `attachments` and status just before the write. If the read returned no
  `attachments` field, stop: a missing field is never "not attached".
- **Match by URL only**, case-insensitively; other attachments are ignored. For a delegated update, a null
  `before.pr_link` means no attachment has the `set` URL, and a URL means one does. If that differs from what the
  re-read shows, the record is a conflict: skip all of it, its other fields included.
- **Leave `links` out** only when the URL is already attached (for a delegated update, when `before` also names it). If
  nothing else is in `set`, make no connector call, read the Issue back and report the record as written.
- **Read back.** Confirm the attachment, and compare the status with the one read before the write. If it changed and
  `set.status` did not ask for that, stop the batch and report it as possible GitHub automation, with that record reported as written.
- **On a timeout or unknown result,** read back before any retry. In a delegated batch, every field as requested counts
  as written; anything else is a failed record, which stops the batch. Never send the link a second time blindly.

## Cross-Entity Rules

- `title` is required on every entity — it is the primary human-readable identifier shown in
  previews and approval prompts.
- Any field named `contained-*`/`dependencies`/`related-*`/`notion-link` stores stable IDs only,
  never display names — see SKILL.md's "never infer a target from a display name" rule. The
  `linked_record` field inside a `disposition-history` entry (see `FOUNDATION_CONTRACTS.md`'s
  Disposition Record) is the same kind of stable-ID reference, scoped to that one array entry
  rather than the whole record. `open-item-source` is the same kind of reference in the opposite
  direction (a stable ID back to the source), but carries its own `{system, stable_id, item_id}`
  shape rather than a bare stable-ID string, since the source can be either Notion or Linear and a
  single source can produce more than one follow-up.
- `status` values are team-configured in Linear itself, not a fixed enum this skill defines — read
  the team's actual configured statuses before proposing a status change rather than assuming a
  generic set (e.g. "Done") exists.
- `disposition-history` is append-only — a dispositioning pass adds entries, it never replaces or
  reorders the array.
