# Linear Entity Fields

Five entity types this skill owns. Each row below lists the fields beyond the shared identity
(stable ID, `transition-id`) that this specific entity type carries — `notion-link` is not a
shared field; only Goal carries it (see its own table below), since it's the only entity type
promotion from Notion produces directly.

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

## Cross-Entity Rules

- `title` is required on every entity — it is the primary human-readable identifier shown in
  previews and approval prompts.
- Any field named `contained-*`/`dependencies`/`related-*` stores stable IDs only, never display
  names — see SKILL.md's "never infer a target from a display name" rule.
- `status` values are team-configured in Linear itself, not a fixed enum this skill defines — read
  the team's actual configured statuses before proposing a status change rather than assuming a
  generic set (e.g. "Done") exists.
