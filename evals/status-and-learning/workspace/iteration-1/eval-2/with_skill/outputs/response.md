# Capturing the CSV Export Learning — Status Check Before I Write Anything

This is an Outcome/Learning capture, which is `status-and-learning`'s job (not
`open-item-management` — that only comes into play afterward if this surfaces open follow-ups).
Following the skill's procedure, I got partway through and hit two real blockers before I'd be
willing to write anything to Notion. Rather than guess past them, here's exactly where I am and
what I need from you.

## Step 1 — Read the relevant Linear facts (blocked)

The skill requires reading the actual Linear facts this outcome is about, via
`linear-work-management`, before drafting a summary — and that skill in turn requires resolving
the target **by stable ID, never by display name**, because Linear names aren't unique across
teams/projects.

"The CSV export feature" is a display name, not an ID, and I don't have a Linear Issue/Project ID
to resolve it against. I'm not going to guess which Issue/Project this refers to.

Separately — and this would block me even with a resolved ID — `linear-work-management`'s own
SKILL.md states its backing connector tools
(`mcp__workmanagement-kit__linear_read`/`linear_write`) have **no backing MCP server
configuration yet**. Per the plugin README's Status section, this plugin is Wave 1 of a two-wave
build, and live Notion/Linear mutation (including reads through the governed connector) requires
Foundational Setup — connector installation, workspace/team scoping — that hasn't landed yet. So
even a correctly-resolved Issue ID wouldn't currently produce a live Linear read.

**What I need from you:** the Linear Issue or Project ID (or a link) for the CSV export work, so
the record's required `related-goal-or-issue` field points at a stable ID rather than a guess.

## Step 2 — Draft the summary content (blocked on facts, not mechanics)

The Outcome/Learning record type (`notion-knowledge-management`'s
`references/notion-record-types.md`) requires:

| Property | Required | What I'd need |
|---|---|---|
| `title` | Yes | e.g. "CSV export — shipped" (can draft this) |
| `related-goal-or-issue` | Yes | Stable Linear ID — **missing** |
| `measured-result` | Yes | What actually happened — **missing** |
| `deviation-from-expected` | No | How it differed from plan, if it did |
| `learning` | No | The takeaway, if distinct from the result |

I don't have any independent source for `measured-result` or the deviation/learning content —
you haven't told me what happened during the shipment (on time? scope cut? a bug found post-ship?
a process insight worth keeping?), and per this skill's data-only boundary, I won't invent facts
just to fill the record. This is also why I'm not fabricating a plausible-sounding "we learned to
validate encoding edge cases" narrative — that would be a made-up fact dressed as a summary,
exactly what the skill's "don't mirror/don't invent" framing warns against.

**What I need from you:** in a sentence or two — what was the actual result of shipping CSV
export, and what's the one thing worth remembering (a deviation from plan, a technical gotcha, a
process takeaway)?

## Steps 2b–5 — Preview, approval, write, read-back (not yet reached)

Once I have both inputs above, I'll:
1. Draft the dated Outcome/Learning record (explicitly labeled as a point-in-time snapshot, never
   implied to be live).
2. Preview it to you for approval before anything is written — this is a required gate per the
   skill's Confirmation and Safety section; I won't skip it even for a small capture.
3. On approval, write it via `notion-knowledge-management` — noting that skill has the identical
   "no backing MCP server configuration yet" gap as `linear-work-management`, so the actual write
   would also need Foundational Setup completed first. If that's still pending when you approve
   the content, I'll say so plainly rather than reporting a write that didn't really happen.
4. Read back both the Linear source and the new Notion record to confirm nothing drifted and
   record the transition.

## Bottom line

Two independent blockers, not one: a missing Linear ID (your input) and a not-yet-wired
Notion/Linear connector (Foundational Setup, per the plugin's own README Status section). Give me
the Issue/Project ID and the actual result/learning, and I'll draft the preview immediately — but
I can't produce a trustworthy Outcome/Learning record, or promise a live write, without both.
