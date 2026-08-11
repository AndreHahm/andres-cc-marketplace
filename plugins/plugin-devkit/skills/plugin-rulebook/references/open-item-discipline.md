# Open-Item Discipline

Two related checks, shared by `plugin-lifecycle-upstream`, `plugin-lifecycle-downstream`, and `plugin-lifecycle-maintenance` — each skill's own SKILL.md/workflow states *when* in its own procedure these run; this file is the single source of truth for *how* they run, so the disclosure wording and bar for "resolved" don't drift out of sync across three separate skills. A third procedure below is specific to `plugin-lifecycle-downstream` alone.

## Phase-Completion Check

**Purpose:** catch a phase (or workflow step) getting marked complete despite owning unresolved sub-work of its own — most commonly a sub-agent dispatch cancelled mid-run by a session limit, but also a batched dispatch where only some batches returned, or a check that was supposed to run against every item in a set but silently stopped partway through.

**Procedure:**
1. Before presenting a phase's gate (or, for a workflow step with no formal gate, before moving on to the next step), review what that phase actually dispatched in this run and confirm each dispatch either completed normally or was explicitly recorded as skipped-with-reason.
2. If any dispatch was cancelled, errored, or left incomplete — a session-limit interruption, a tool crash with no retry, a batch that never returned — do not present the phase as cleanly complete. State plainly what didn't finish, and what (if anything) still needs a follow-up run.
3. This is a disclosure requirement, not a blocking one: an incomplete sub-dispatch does not have to be resolved before the phase can advance — the run can proceed with the gap named as an open item, the same non-blocking-disclosure pattern `plugin-lifecycle-upstream`'s own "unplanned overhead" note at its Test gate already uses for a comparable class of mid-run friction.

## Pre-Commit Disclosure

**Purpose:** catch a run that reaches a commit step while findings surfaced earlier in that same run — an unaddressed Self-Review finding, a Test failure recorded as skipped, a Phase-Completion gap from an earlier phase — were never explicitly resolved or explicitly declined by the user.

**Procedure:**
1. Immediately before any Commit step in any of the three lifecycle skills, collect every open item surfaced during the current run: Phase-Completion gaps (above), Self-Review findings the user didn't approve for action, Test/smoke-check failures or skips, items an `enhancement-suggestor` plan classified as non-Quick-Win (Strategic Investment / Reconsider), Quick Wins the user declined, and any other item explicitly flagged but left unresolved.
2. If the list is non-empty, state it plainly to the user as part of presenting the commit (file list + message) — before the commit itself runs, not folded silently into the commit message and not omitted on the assumption the user already saw it earlier in the run. For a deferred-by-classification item specifically, state its classification label and one-clause reason, not just its name — pull this from `enhancement-suggestor`'s own `## Deferred Items` list rather than re-deriving it. If the commit message itself carries a `Deferred:` line, that line must also state the reason, not only the item name.
3. An empty list is a normal, common outcome — state "no open items" rather than omitting the line entirely, so its absence isn't mistaken for the check not having run at all.

## Downstream's Proactive Offer

**Scope:** `plugin-lifecycle-downstream` only. The other two lifecycle skills stop at the Pre-Commit Disclosure above; this is an addition specific to downstream's own end-of-run behavior, not a shared procedure.

**Procedure:** at the end of a downstream run, if any open item remains — from Pre-Commit Disclosure, or surfaced afterward (e.g. a declined Deep Test, an unresolved Self-Review finding from Phase 5) — do not just list the items and stop. Ask via `AskUserQuestion`: "N open item(s) remain from this run — implement them now?", with per-item or consolidated options to proceed. This mirrors the same "offer the next step, don't just report and end" pattern downstream's own Suggested Next Step already uses for Phase 3/Deep Test, applied here specifically to items that would otherwise be left to a future, unscheduled run — or forgotten.

## Why This Is Shared, Not Restated Per Skill

Three lifecycle skills, three different phase structures — but "did this phase's own work actually finish" and "does the user know what's still open before we commit" are the same two questions regardless of which pipeline is asking them. Keeping the wording and the disclosure bar in one file means a future change to either check (e.g. tightening what counts as "explicitly resolved") lands once, not three times across three separately-maintained SKILL.md files — the same reasoning `branch-and-pr-preflight.md` already established for the Open-PR and Branch-scope checks.
