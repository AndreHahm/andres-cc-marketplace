---
name: plugin-conception
description: >-
  Turns a rough idea, imported draft, or recent-session evidence of friction, failure, or
  opportunity into a decision-ready classification (Create, Enhance, Repair, Consolidate,
  Reposition, Retain, Reject/Defer) before plugin-ideation's interview or plugin-planning/Fix
  begins. Runs a shared normalize/classify/shallow-overlap-check core from either starting point,
  then produces a Conception Brief whose depth matches the classification — light for Create
  (hands off to plugin-ideation unchanged), full for every other outcome (marketplace
  integration, implementation plan, baseline contract). Use when the user asks "should this be a
  new plugin or an enhancement", "classify this idea", "is this new or should it extend X", "turn
  these session findings into a concept", or has a rough idea or session evidence that needs
  qualifying before ideation or planning/Fix runs. Not a replacement for plugin-ideation's
  interview or plugin-planning's component inventory — this is the qualifier that precedes both.
argument-hint: "[rough idea, problem statement, or session-evidence source]"
allowed-tools: Read Glob Grep Write Bash(date:*) Skill
---

# Plugin Conception

Turns either a rough idea or evidence of an unmet need into a decision-ready classification before
`plugin-ideation`'s interview, `plugin-planning`'s component inventory, or `plugin-lifecycle-maintenance`'s
Fix phase begins. This is a **pre-ideation, pre-planning qualifier**, not a replacement for the deeper work
either downstream skill already does — it establishes that a proposed change is useful, distinct,
appropriately placed, bounded, and worth the next phase's cost, then hands off.

**Conception is a classification pass, not an interview.** Unlike `plugin-ideation`'s multi-round
back-and-forth, this skill interviews the requester only where a missing answer would change the
classification or the shallow overlap read — never to `plugin-ideation`'s depth, and never re-asking
questions `plugin-ideation` will ask again immediately after a Create handoff.

## Quick Start

1. **Route** — from-scratch idea, or recent-session evidence? (Entry Routes A/B)
2. **Normalize and classify** — build a problem frame, label assumptions, then classify: Create / Enhance / Repair / Consolidate / Reposition / Retain / Reject-Defer (Steps 1-2)
3. **Check overlap, shallow only** — repository-metadata depth; confirms or revises the classification (Step 3)
4. **Define the concept, non-Create only** — full depth, implementation plan, workflow if procedural (Steps 4-6; Create skips straight to Step 7)
5. **Decide and hand off** — approve / revise / merge / defer / reject; write the Conception Brief (Step 7)

## When to Use

- Before `plugin-ideation`'s interview, to confirm a rough idea is actually worth that interview (or is
  really an Enhance/Consolidate in disguise)
- Before `plugin-planning`/`plugin-lifecycle-maintenance`'s Fix phase, to turn session evidence, a finding,
  or an enhancement request into a bounded, evidence-backed concept with a baseline contract
- Invoked automatically as Phase 1 (Conceive) of `plugin-lifecycle-upstream`, or as a step inside
  `plugin-lifecycle-maintenance`'s `improve-a-plugin`/`enhance-a-plugin` workflows, immediately after their
  own human finding-selection gate

## When NOT to Use

- The concept is already a Create classification with a clear problem statement and nothing left to
  qualify — go straight to `plugin-ideation`; running this skill first only to immediately hand off is
  needless ceremony when the classification was never in doubt
- A narrow repair with an already-known fix and an already-accepted finding — see "Bypass for narrow
  repairs" under Step 2; hand off directly to Fix instead
- Deep per-component overlap search, activation-trigger overlap analysis, or naming-candidate validation —
  that's `plugin-ideation` Step 3-4's job (Create) or the type-matched reviewer agents' job (everything
  else), never this skill's
- Scaffolding components, editing production plugins, or running QA fixes — this skill produces a brief,
  never files
- Already committed to running the full guided pipeline (Conceive→Ideate→Plan→Design→Build), not just the
  classification step — use `plugin-lifecycle-upstream` instead; it dispatches here automatically as
  Phase 1, so invoking this skill directly is for when the classification decision itself is the goal
- Already committed to acting on retro/comparison findings against an already-shipped plugin, with
  apply/test/commit follow-through — use `plugin-lifecycle-maintenance`'s `improve-a-plugin`/
  `enhance-a-plugin` workflows instead; they dispatch here automatically after the human finding-selection
  pick, so invoking this skill directly is for classifying a rough idea or evidence source before any
  pipeline commitment exists

## Entry Route A: Start From Scratch

Use when the starting point is a rough idea, problem statement, desired capability, or proposed
plugin/skill. If `$ARGUMENTS` is given, treat it as the rough idea or problem statement directly — the
same way `plugin-ideation`'s own Step 2 treats a detailed `$ARGUMENTS` — and reflect it back rather than
re-asking for it from scratch. Minimum intake, deliberately light since a Create outcome hands off to
`plugin-ideation`'s own deeper interview rather than duplicating it here:

- the problem or opportunity;
- the concrete user and usage situation, at whatever resolution the requester already has it;
- the intended outcome;
- known constraints and explicit non-goals, as far as they're already known;
- any existing component the requester believes is adjacent.

Interview the requester only where a missing answer changes classification or the shallow overlap read.
Do not fabricate evidence that does not exist, and do not require a retrospective the requester never
asked for.

## Entry Route B: Start From Recent-Session Evidence

Use when repeated friction, failures, gaps, or opportunities have been observed in one or more recent
sessions — session-analysis reports, build handoff reports, validation/grading/comparison/security/
completeness/consistency findings, user corrections, or durable planning artifacts. If `$ARGUMENTS` names
one of these sources directly (a report path, or one entry from a findings bundle or approved suggestion
list an upstream workflow's own human-decision gate already produced), treat it as the evidence source for
Step 1 below rather than re-deriving it. **This skill classifies and briefs exactly one candidate per
invocation** — when a caller's own gate approved several candidates at once (e.g.
`plugin-lifecycle-maintenance`'s multiSelect finding-selection pick), it invokes this skill once per
candidate, never once with the whole list; this skill's own Step 1 never fans a single invocation out into
multiple classifications or multiple briefs. Session evidence is a **seed, not the scope** of the concept.
See `references/evidence-routing.md` for the full 6-step
evidence-handling procedure (identify source, recheck currency, separate symptoms from underlying need,
merge duplicates, discard stale/non-actionable, obtain explicit approval before promoting to a planned
change) and the evidence-source list. If evidence is insufficient, fall back to Entry Route A's focused
interview — never require a full retrospective the desired concept doesn't actually depend on.

Most session evidence classifies as Enhance, Repair, or Consolidate rather than Create — those
classifications get the full Conception Brief (Steps 4-5 below), since `plugin-lifecycle-maintenance`'s
existing workflows have no equivalent deep-definition step of their own.

## Step 1: Normalize Intent and Evidence

Build a concise problem frame from whichever entry route ran:

- problem or opportunity;
- target user and concrete scenario;
- desired outcome;
- supporting evidence or assumptions;
- constraints and non-goals;
- success signals.

Label every assumption explicitly. Every piece of evidence must identify its source. Never rely on an
unverified claim that a capability is absent or broken — check the current repository state instead of
trusting a stale report.

## Step 2: Classify the Proposed Change

| Classification | Meaning | Likely destination |
|---|---|---|
| Create | No suitable existing capability; add a new plugin or component | `plugin-ideation`, then the rest of the upstream pipeline |
| Enhance | Preserve an existing component and add or improve behavior | `plugin-planning` (if new components are needed) or directly to Fix |
| Repair | Restore behavior that contradicts the current contract | Directly to Fix — usually skips the full brief (see below) |
| Consolidate | Multiple components overlap and should be merged or have clearer boundaries | `plugin-planning` plus consistency/activation review |
| Reposition | Capability exists but belongs in a different plugin or functional group | `plugin-planning` and marketplace restructuring |
| Retain | Current behavior is adequate; no implementation is justified | Stop with rationale |
| Reject/Defer | Benefit, evidence, feasibility, or priority is insufficient | Stop or record a revisit condition |

The classification may change after Step 3's overlap check — an apparent Create may turn out to be Enhance
or Consolidate, and, just as often, an apparent Enhance may turn out to be a genuine Create once the
shallow check shows nothing adjacent actually exists.

**Bypass for narrow repairs:** a Repair classification with an already-known, narrowly-scoped fix and an
already-accepted finding does not need the full brief (Steps 4-5) — record the classification and
evidence, then hand off directly to Fix. This keeps the skill proportional rather than adding ceremony to
a one-line fix.

## Step 3: Check Overlap and Marketplace Fit — Shallow, Classification-Level Only

This check is deliberately shallow. Its only job is to confirm or revise Step 2's classification — never
the exhaustive per-component search `plugin-ideation` runs immediately after a Create handoff, and never
the deep evidence-gathering the finding-source tools already ran before this skill started.

Inspect, at repository-metadata depth only:

- plugin manifests and plugin purposes;
- skill, agent, command, hook, and rule descriptions;
- existing lifecycle ownership;
- related draft concepts and generated reports.

| Overlap | Meaning |
|---|---|
| None | Step 2's classification likely holds; proceed |
| Partial | Classification may need to shift toward Enhance/Consolidate; reconsider before proceeding |
| Full | Classification shifts to Retain or Enhance; a Create outcome is very unlikely to survive this finding |

**Do not, here:** activation-trigger overlap analysis, cross-component reference tracing, or
naming-candidate validation — escalating past metadata-level inspection is the single most common way this
skill ends up duplicating `plugin-ideation`. Marketplace placement follows the repository convention: a
plugin uses `<domain>-kit` or `<domain>-devkit`, exactly one hyphen immediately before the suffix. For
Create outcomes, this skill never proposes a name — that's `plugin-ideation` Step 4's job. For every other
outcome, record the existing plugin's placement, not a new name.

## Step 4: Define the Concept — Full Depth Only for Non-Create

**Create:** skip this step entirely. Step 1's problem frame plus the classification and Step 3's shallow
overlap result is the whole Create handoff payload.

**Enhance / Repair (full-brief) / Consolidate / Reposition:** the accepted concept must specify a
one-sentence value proposition, target users and triggering situations, in-scope capabilities, explicit
non-goals, whether the target is a new component or a change to an existing one (never a new plugin — that
would be a Create by definition), the proposed marketplace owner and neighboring components,
dependencies/consumers/lifecycle handoffs, compatibility requirements for existing behavior, measurable
acceptance criteria, principal risks and mitigations, and a baseline contract (behavior that must remain
unchanged, observed deficiency and evidence, proposed delta, affected callers/docs/tests/activation
triggers, rollback or rejection conditions).

## Step 5: Shape the Implementation Plan

**Create:** skip this step — `plugin-planning` (reached after `plugin-ideation` completes) owns
component-type/count/depth decisions.

**Every other non-bypassed classification:** define target files/component directories, required new or
modified components, dependency/integration changes, tests or evaluations that demonstrate the concept,
documentation changes, validation/review/commit boundaries, and a recommended execution order. Detailed
prompts, scripts, schemas, and line-level edits still belong in the subsequent planning/design phase — not
here.

## Step 6: Describe the Workflow When the Concept Is Procedural

Include a workflow only when the proposed capability coordinates three or more dependent states, gates, or
handoffs — entry conditions, ordered phases, artifacts consumed/produced, human approval gates, stop/
retry/resume behavior, downstream owner per handoff, completion criteria. A single focused skill does not
need an invented workflow merely to fill this section — mark it not applicable with a one-sentence reason
instead.

## Step 7: Decide and Hand Off

Present the completed brief via `AskUserQuestion`: approve and proceed / revise / merge with an existing
concept / defer with a revisit condition / reject or retain the current state. Only an approved concept
proceeds — this skill never auto-applies findings or silently turns evidence into a feature.

1. Get a timestamp: `date -u +%Y-%m-%dT%H-%M-%SZ`
2. Write to `.claude/output/plugin-conception/<concept-slug>-<timestamp>.md` per
   `references/conception-brief-template.md` — for Create, the light variant its own blockquote
   instructs (the section list lives there, not restated here, to avoid drift); for everything else, all
   12 sections in full
3. Present the artifact link first, then the summary:

```
📄 Conception Brief written: `.claude/output/plugin-conception/<concept-slug>-<timestamp>.md`
```

Hand-off target follows the classification:

- **Create →** `plugin-ideation`, with the light brief as its input.
- **Enhance / Consolidate / Reposition →** `plugin-planning` if new or restructured components are
  implied, otherwise directly to `plugin-lifecycle-downstream`'s Phase 8 (Consolidated Fix).
- **Repair (full-brief path) →** directly to `plugin-lifecycle-downstream`'s Phase 8 (Consolidated Fix).
- **Retain / Reject / Defer →** stop; no downstream hand-off.

**Standalone invocation:** ask via `AskUserQuestion` before invoking the hand-off target — never invoke it
silently.

**Nested invocation:** when this skill runs as a step inside another orchestrator — `plugin-lifecycle-upstream`'s
Phase 1 (Conceive), or `plugin-lifecycle-maintenance`'s `improve-a-plugin`/`enhance-a-plugin` Conceive step —
the brief-content approval above (approve/revise/merge/defer/reject) still runs, but the hand-off
**invocation** does not: this step ends at "write the brief and report its classification." The calling
orchestrator owns deciding where each classified candidate goes next, since it may be routing several
candidates from one run — that decision may be a single consolidated `AskUserQuestion` (as
`plugin-lifecycle-upstream`'s Gate 1 does) or a deterministic routing rule stated plainly to the user with
no further ask (as `plugin-lifecycle-maintenance`'s `improve-a-plugin`/`enhance-a-plugin` Step 4 does,
routing by classification alone). Either way, never ask twice for the same decision — see those two
callers for how each owns this instead.

## Resume Behavior

- A draft brief resumes at the first incomplete section (light briefs have fewer sections to resume
  through).
- An approved brief resumes at handoff after the user confirms it is still current.
- Evidence is rechecked when the underlying target has changed since approval.
- A legacy Concept Card may still be read directly by `plugin-ideation` without ever passing through this
  skill — conception is not a mandatory gate in front of an already-existing Concept Card.

## Stop Conditions

Stop without implementation when: full overlap makes a new component unnecessary; current behavior
satisfies the verified need; evidence is stale or already resolved; the concept lacks a concrete user
outcome; marketplace ownership cannot be decided without a user choice; risks or cost exceed the accepted
benefit; or the user defers or rejects the concept. A clean stop is a valid result and must include its
rationale — never silently drop a concept without stating why.

## Testing & Validation

**Eval evidence:** `evals/plugin-conception/evals.json` — 8 scenarios (Quick Workflow, `workspace/iteration-1`), 7/8 eval-covered (scenario 1's eval is invalidated by a scripted-premise flaw unrelated to this skill's behavior — see its own `grading.json`); the remaining scenarios below are design-review-verified.

1. **From-scratch Create** — a rough idea with no session evidence; confirm the light brief (per
   `references/conception-brief-template.md`'s own light-variant section list) is produced and handed to
   `plugin-ideation`, never a padded-out full brief
2. **Session-evidence Enhance** — evidence pointing at friction with an existing component; confirm the
   full brief is produced (all 12 sections) with a populated baseline contract
3. **Full overlap** — an idea that duplicates an existing component; confirm the classification shifts to
   Retain/Enhance and the skill stops with rationale rather than proceeding toward Create
4. **Stale evidence** — session evidence describing a since-fixed gap; confirm Step 1's current-state
   reverification catches this and the evidence is discarded, not promoted
5. **Narrow-repair bypass** — a Repair classification with an already-known fix and an accepted finding;
   confirm Steps 4-5 are skipped and the skill hands off directly to Fix
6. **Consolidate** — multiple overlapping components found during Step 3; confirm the full brief is
   produced and `plugin-planning` plus consistency/activation review are named as the destination
7. **Retain/no-work outcome** — evidence that current behavior is already adequate; confirm a clean stop
   with stated rationale, no brief written
8. **Create brief stays light** — construct a Create classification with rich session evidence available;
   confirm the written brief still marks Scope and Boundaries, Existing-Component Baseline, Implementation
   Plan, and the "eventual implementation success" half of Acceptance Criteria as not applicable, rather
   than restating what `plugin-ideation`/`plugin-planning` will produce

**Quality gates:**
- [ ] Step 3's overlap check never exceeds repository-metadata depth — no activation-trigger analysis,
      cross-component reference tracing, or naming-candidate validation
- [ ] A Create classification's brief always marks Scope and Boundaries, Existing-Component Baseline,
      Implementation Plan, and the "eventual implementation success" half of Acceptance Criteria not
      applicable — never a padded-out 12-section document
- [ ] The narrow-repair bypass (Step 2) is only ever taken when the fix is already known and the finding
      already accepted — never for an undefined or contested repair
- [ ] Entry Route B evidence is always rechecked against current repository state before promotion — never
      copied forward from a source artifact unverified
- [ ] Step 7's decision is always made via `AskUserQuestion` — this skill never auto-applies a finding or
      silently promotes evidence into a planned change
- [ ] **Standalone invocation:** the hand-off target is always invoked via `AskUserQuestion` confirmation
      first — never invoked silently. **Nested invocation** (inside `plugin-lifecycle-upstream`'s Phase 1
      or `plugin-lifecycle-maintenance`'s Conceive step): no hand-off is invoked from here at all — only
      the brief-content approval fires; the calling orchestrator owns the hand-off routing decision (a
      consolidated ask, or a plainly-stated deterministic rule)
- [ ] The Conception Brief path is always under `.claude/output/plugin-conception/`
- [ ] A clean stop (Retain/Reject/Defer/full overlap/stale evidence) always states its rationale — never a
      silent drop

## Reference Guide

| Resource | Type | Purpose |
|---|---|---|
| `scripts/smoke_test.py` | In this skill | This skill's own persisted smoke test (frontmatter validity, referenced-file existence, Bash-scope grant consistency) — re-run after any SKILL.md edit |
| `evals/plugin-conception/` | Repo root | Persisted `skill-tester` Quick Workflow eval suite (8 scenarios, 7/8 covered) |
| `references/conception-brief-template.md` | In this skill | Light and full Conception Brief templates used in Step 7 |
| `references/evidence-routing.md` | In this skill | Entry Route B's evidence sources and the 6-step evidence-handling procedure |
| `plugin-ideation` skill | Sibling skill | Create-classification hand-off target — owns the interview, deep overlap search, and naming |
| `plugin-planning` skill | Sibling skill | Hand-off target for Enhance/Consolidate/Reposition outcomes implying new or restructured components |
| `plugin-lifecycle-downstream` skill | Sibling skill | Owns Phase 8 (Consolidated Fix) — hand-off target for Repair and no-new-component Enhance outcomes |
| `plugin-lifecycle-upstream` skill | Sibling skill | Runs this skill as Phase 1 (Conceive) |
| `plugin-lifecycle-maintenance` skill | Sibling skill | Runs this skill as a step inside `improve-a-plugin`/`enhance-a-plugin`, after the human finding-selection gate |
