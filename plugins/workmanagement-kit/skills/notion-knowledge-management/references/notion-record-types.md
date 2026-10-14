# Notion Record Types

Seven record types this skill owns. Each row below lists the properties beyond the shared set
(`source`, `related-record`, `authority`, `transition-id`, `owner`, `date`, `repo`, and `status` — except
on Decision, where `decision-state` is the sole authoritative state instead, see SKILL.md's
Decision State Machine section — see SKILL.md) that this specific type requires or supports.

## Idea

| Property | Required | Notes |
|---|---|---|
| `title` | Yes | Short, human-readable summary |
| `area` | Yes | Domain/category tag, for later filtering |
| `body` | Yes | The idea's own content |
| `linear-link` | No | Populated by `work-linking` after `idea-to-implementation` promotes this Idea |

## Decision

| Property | Required | Notes |
|---|---|---|
| `title` | Yes | Short, human-readable summary |
| `context` | Yes | Why this decision is being made |
| `alternatives` | Yes | Options considered, even if only one was seriously weighed |
| `consequences` | Yes | Expected effects of the choice |
| `decision-state` | Yes | `proposed` / `accepted` / `superseded` / `reversed` — see SKILL.md's Decision State Machine |
| `supersedes` / `superseded-by` | No | Set only on the superseding/superseded pair |
| `related-artifact` | No | Idea, Report, or other record this Decision responds to |
| `linear-link` | No | Populated by `work-linking` after `idea-to-implementation` promotes this Decision |
| `disposition-history` | No | Array of per-item outcomes recorded by `open-item-management` when this Decision is the open-item source; accumulates, never overwritten — see `FOUNDATION_CONTRACTS.md`'s Disposition Record |

## Proposed Goal

| Property | Required | Notes |
|---|---|---|
| `title` | Yes | Short, human-readable summary |
| `description` | Yes | What the Goal is and why it matters |
| `related-decision` | No | The Decision (if any) that motivated this Goal |
| `readiness-notes` | No | Open questions/dependencies before this could be accepted into Linear |
| `linear-link` | No | Populated by `work-linking` after `idea-to-implementation` promotes this proposed Goal |

## Note

| Property | Required | Notes |
|---|---|---|
| `title` | Yes | Short, human-readable summary |
| `category` | Yes | Free-text categorization |
| `body` | Yes | The note's own content |

## Research

| Property | Required | Notes |
|---|---|---|
| `title` | Yes | Short, human-readable summary |
| `question` | Yes | What was being investigated |
| `findings` | Yes | What was learned |
| `source-link` | No | External reference, if any |

## Report

| Property | Required | Notes |
|---|---|---|
| `title` | Yes | Short, human-readable summary |
| `summary` | Yes | Executive summary of the report's content |
| `body` | Yes | A short note only (at most 2,000 characters); the full report goes into page content as blocks — see SKILL.md's Long Text and Page-Content Blocks |
| `open-items` | No | Enumerated follow-ups — feeds `open-item-management` |
| `disposition-history` | No | Array of per-item outcomes recorded by `open-item-management` when this Report is the open-item source; accumulates, never overwritten — see `FOUNDATION_CONTRACTS.md`'s Disposition Record |

## Outcome / Learning

| Property | Required | Notes |
|---|---|---|
| `title` | Yes | Short, human-readable summary |
| `related-goal-or-issue` | Yes | The Linear work this outcome is about |
| `measured-result` | Yes | What actually happened |
| `deviation-from-expected` | No | How this differed from what was planned, if it did |
| `learning` | No | The takeaway, if distinct from the measured result |

## Cross-Type Rules

- `title` is required on every type — it is the primary human-readable identifier shown in
  previews and approval prompts.
- `related-record`/`related-*` fields always store a stable ID, never a display name.
- `repo` is a required select property on every type, set from the plugin's `notion.repo`
  configuration value (`FOUNDATION_CONTRACTS.md` at the plugin root), never from the record's content or a
  caller's message. It must equal an existing option; if `notion.repo` is unset or matches no option,
  stop and report instead of writing the record without it. Note, Research and Outcome/Learning live in
  organization-level databases shared by all repositories, so `repo` is what tells their rows apart; the
  other four types live in a per-repository database and carry `repo` for uniformity.
- **Reading the shared databases:** a read, search or query of Note, Research or Outcome/Learning can
  return another repository's rows. Treat `repo` as attribution: show each row's `repo` in the results,
  never present a row as this repository's without it, and filter by `repo = notion.repo` only when the
  user asks for this repository's records. Take the filter value from `notion.repo`, never from a record.
- No text property on any type may hold more than 2,000 characters. SKILL.md's Long Text and
  Page-Content Blocks section owns the rule and what to do about a longer value; it covers the Idea
  and Note `body`, Decision `context` and Research `findings` rows as well as a Report's `body`.
- No type in this table supports a delete operation — see SKILL.md's Gotchas.
- `disposition-history` is append-only — a dispositioning pass adds entries, it never replaces or
  reorders the array.
