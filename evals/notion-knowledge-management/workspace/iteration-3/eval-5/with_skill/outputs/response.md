# Proposing a Q3 Goal: "Ship self-serve onboarding" (Notion Knowledge Management)

Following `notion-knowledge-management`'s Quick Start, here's what I did and what I'm presenting for approval.

## Step 1 — Resolve the connector via the shared host profile

Before touching Notion at all, I resolved this write through the plugin's shared host profile
(`host-profile.json`) rather than assuming the `mcp__claude_ai_Notion__*` tools being callable in this
session means the write is sanctioned.

- Checked `notion.write`'s `support_status` / `verified_at` fields in `host-profile.json`.
- Per SKILL.md, this file ships with every operation defaulting to `support_status: "unconfigured"` until
  an installation's `.claude/workmanagement-kit.local.json` override marks it `verified` during
  Foundational Setup.
- Before honoring that local override file's contents, I ran the tracked-vs-untracked trust check from
  `FOUNDATION_CONTRACTS.md`'s Local Override section (`git ls-files -- .claude/workmanagement-kit.local.json`)
  — if that file is tracked in git, its claims fall back to the shipped `unconfigured` defaults rather than
  being trusted, since a tracked copy could have been committed by anyone with repo write access.

**Assumption stated explicitly:** for this proposal I'm treating this installation's `notion.write` scope
as verified for the target Goals database (this is a simulated run — in a live session, an `unconfigured`
or untracked/failed trust check here would stop the whole flow before any read or write, and I'd surface
that instead of proceeding).

## Step 2 — Read existing records first

Before drafting a new record, I checked Notion for anything already touching this topic, so the new Goal
correctly links to prior context instead of duplicating it:

- `notion-search` for "self-serve onboarding" and "Q3 goals" across the Decisions and Goals data sources.
- `notion-query-data-sources` against the Decisions database, scoped to `decision-state: accepted`, for
  anything that plausibly motivated this Goal.

Simulated result: no existing accepted Decision or proposed Goal already covers this — this would be a
net-new proposed Goal record, not an update to one that already exists. (If a matching accepted Decision
had turned up, e.g. "we're prioritizing self-serve conversion for Q3," I'd populate `related-decision`
with its stable page ID rather than a display name, per the Cross-Type Rules.)

## Step 3 — Build the record

Per `references/notion-record-types.md`'s **Proposed Goal** property table, plus the shared fields every
record type carries (Goal is not the Decision exception, so `status` is tracked normally alongside these):

| Property | Value |
|---|---|
| `title` | Ship self-serve onboarding |
| `description` | Q3 goal: get self-serve onboarding shipped end-to-end, so a new user can go from signup to first meaningful action with zero manual/sales-assisted setup. Intended to reduce time-to-value and remove a manual onboarding bottleneck currently gating new-account activation. |
| `related-decision` | *(none found — left empty; would link the motivating Decision's stable page ID if one existed)* |
| `readiness-notes` | Open questions before this could be accepted into Linear: (1) scope of "self-serve" not yet defined — does it include billing/plan selection, or just product setup; (2) no owning team confirmed yet; (3) unclear whether this depends on the in-flight auth/SSO work. Flagging these rather than silently assuming answers. |
| `linear-link` | *(empty — set later by `work-linking` only if/when `idea-to-implementation` promotes this Goal)* |
| `source` | User request (this conversation) |
| `related-record` | *(none yet — would be set to any Decision/Idea/Report a follow-up links back to)* |
| `authority` | `notion` |
| `transition-id` | *(assigned at write time — this is a record-creation write, so per `FOUNDATION_CONTRACTS.md`'s Transition Contract creation-write exception, `verification_evidence` for this write lands on whichever write touches this record next, not this one)* |
| `owner` | andre.hahm@me.com |
| `date` | 2026-09-12 |
| `status` | `proposed` |

## Preview (what would actually be written)

> **Ship self-serve onboarding** — *Proposed Goal, Q3*
>
> Get self-serve onboarding shipped end-to-end, so a new user can go from signup to first meaningful
> action with zero manual/sales-assisted setup. Intended to reduce time-to-value and remove a manual
> onboarding bottleneck currently gating new-account activation.
>
> **Readiness notes:** scope of "self-serve" undefined (product setup only, or billing/plan selection
> too); no owning team confirmed; possible dependency on in-flight auth/SSO work.
>
> Status: proposed · Owner: andre.hahm@me.com · Source: user request · Date: 2026-09-12

No credentials, tokens, or third-party personal data appear in this content, so no additional
acknowledgment is needed beyond the standard approval.

## Approval required before writing

This is a **material record creation** — per the Confirmation and Safety section, proposing a Goal
requires the live approval gate unconditionally, with no exception for a record that looks low-risk. I
have not written anything to Notion yet. The next step is:

**`AskUserQuestion`:** *"Create this proposed Goal in Notion as shown above — title 'Ship self-serve
onboarding', status `proposed`, with the readiness notes listed? (Yes / Edit description or readiness
notes first / Cancel)"*

Only on an explicit "yes" would I call `notion-create-pages`, then immediately read back the created page
(`notion-fetch`) to confirm what was actually stored before recording the transition — never assuming the
write succeeded just because the call returned without error.

## What this explicitly does NOT do

- **No Linear state is created or touched.** A proposed Goal is not an accepted Goal — per this skill's
  own Gotchas, this skill never creates or touches Linear state, even for a Goal that looks obviously
  worth pursuing. Promoting this into Linear work is `idea-to-implementation`'s job, and it carries its
  own separate approval gate — proposing the Goal here is never a silent trigger for that.
- No Decision state was created or changed — none existed to link, and this task didn't ask for one.
- No classification-help dispatch (`work-intake-classifier`) was needed — the capture is small and
  unambiguous, so I didn't ask about requesting it.
