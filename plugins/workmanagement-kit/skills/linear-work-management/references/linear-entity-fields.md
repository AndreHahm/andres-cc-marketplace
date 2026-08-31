# Linear Entity Fields

Five entity types this skill owns. Each row below lists the fields beyond the shared identity
(stable ID, `transition-id`) that this specific entity type carries — `notion-link` is not a
shared field; only Goal, Project/Initiative, and Issue carry it (see their own tables below),
since those are the entity types `idea-to-implementation`'s own promotion mapping actually
targets (see `promotion-hierarchy-mapping.md`'s Typical Mappings table — an Idea typically
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

## Project / Initiative

| Field | Required | Notes |
|---|---|---|
| `title` | Yes | Short, human-readable summary |
| `lead` | Yes | Owning individual |
| `team` | Yes | Owning Linear team |
| `target-date` | No | Expected completion |
| `contained-milestones` | No | Stable IDs of Milestones under this Project |
| `notion-link` | No | The Idea or accepted Decision record this was promoted from, if promoted via `idea-to-implementation` |

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
| `notion-link` | No | The Idea or accepted Decision record this was promoted from, if promoted via `idea-to-implementation` — the required reciprocal half of `work-linking`'s stable-ID pair for this plugin's most common promotion path |
| `disposition-history` | No | Array of per-item outcomes recorded by `open-item-management` when this Issue is the open-item source; accumulates, never overwritten — see `../../../FOUNDATION_CONTRACTS.md`'s Disposition Record |
| `open-item-source` | No | `{system, stable_id}` reference back to the Report/Decision/Issue this follow-up was created from by `open-item-management`; set directly as part of this Issue's own creation write, independent of the source record's own `disposition-history` — see `../../../FOUNDATION_CONTRACTS.md`'s Disposition Record companion-field note |

## Cross-Entity Rules

- `title` is required on every entity — it is the primary human-readable identifier shown in
  previews and approval prompts.
- Any field named `contained-*`/`dependencies`/`related-*`/`notion-link` stores stable IDs only,
  never display names — see SKILL.md's "never infer a target from a display name" rule. The
  `linked_record` field inside a `disposition-history` entry (see `FOUNDATION_CONTRACTS.md`'s
  Disposition Record) is the same kind of stable-ID reference, scoped to that one array entry
  rather than the whole record. `open-item-source` is the same kind of reference in the opposite
  direction (a stable ID back to the source), but carries its own `{system, stable_id}` shape
  rather than a bare stable-ID string, since the source can be either Notion or Linear.
- `status` values are team-configured in Linear itself, not a fixed enum this skill defines — read
  the team's actual configured statuses before proposing a status change rather than assuming a
  generic set (e.g. "Done") exists.
- `disposition-history` is append-only — a dispositioning pass adds entries, it never replaces or
  reorders the array.
