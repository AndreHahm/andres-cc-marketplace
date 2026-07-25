---
name: plugin-planning
description: >-
  Turns an accepted plugin or component concept into a concrete component inventory —
  which skills, agents, commands, and hooks to build, how many, and how much content
  depth each needs (Minimal/Standard/Rich, reusing this plugin's own 80% Rule and
  skill-category vocabulary rather than a new rubric). Use when the user asks to "plan
  the architecture", "decide what components I need", "plan this plugin's structure",
  or has an accepted plugin-ideation Concept Card ready for the next step. Produces a
  component inventory and depth plan, not designed components — see the matching Design
  skill (skill-development, agent-development, command-development, hook-development,
  rule-development) for that.
argument-hint: "[path to Concept Card, or a direct description]"
allowed-tools: Read Glob Grep Write Bash(date:*) Skill
---

# Plugin Planning

Turns an accepted concept into a concrete build list: which components, how many, and how much content depth each one needs — before any single component is designed. Second step of the upstream lifecycle, after `plugin-ideation` and before per-component Design.

## Quick Start

1. **Load the concept** — read the Concept Card, or take a direct description if the user skipped ideation (Step 1)
2. **Decide component types** — skills vs. agents vs. commands vs. hooks, and how many of each (Step 2)
3. **Allocate content depth** — Minimal / Standard / Rich per planned skill (Step 3)
4. **Map to functional groups** — cluster related components so Design work stays coherent (Step 4)
5. **Write the plan** — `.claude/output/plugin-planning/<slug>-<timestamp>.md` (Step 5)

## When to Use

- Right after `plugin-ideation` produces an accepted Concept Card
- The user already knows roughly what they want but hasn't decided component types/counts/depth yet
- Deciding how much `references/`/`examples/`/`scripts/` content a planned skill will need, before writing any of it

## When NOT to Use

- No concept yet — run `plugin-ideation` first
- A single, already-well-understood component — skip straight to the matching Design skill; planning overhead isn't worth it for one obvious skill
- Reviewing or scoring an *existing* plugin — use `plugin-grader` instead
- Actually designing a component's procedure/frontmatter/body — that's `skill-development`/`agent-development`/`command-development`/`hook-development`/`rule-development`'s job, not this skill's
- Wanting the full guided Ideate→Plan→Design→Build pipeline rather than just this step — use `plugin-lifecycle-upstream` instead (it dispatches here automatically)

## Step 1: Load the Concept

Take `$ARGUMENTS` as either a Concept Card path or a direct description. If it resolves to an existing file under `.claude/output/plugin-ideation/`, `Read` it in full. Otherwise treat `$ARGUMENTS` as the problem statement directly (user skipped `plugin-ideation`) and proceed — note in the plan that ideation was skipped, so a reader knows the overlap check wasn't run.

## Step 2: Decide Component Types and Counts

For each distinct capability the concept implies, decide the component type using this decision matrix (extends `plugin-development`'s own Component Overview table with the multi-signal criteria that table doesn't itself spell out):

| Signal | Component type |
|---|---|
| User-invoked action or specialized knowledge, single coherent domain | Skill |
| Isolated, autonomous decision-making with restricted tools, invoked by another component | Agent |
| Simple, single-file user-invoked action, no supporting content needed | Command (legacy format — prefer a Skill unless the plugin already uses `commands/`) |
| Event-driven automation triggered by tool use or session lifecycle | Hook |

List each planned component: name candidate, type, one-line purpose, and rough trigger phrases.

**Code smell check:** if the plan proposes more than 4 agents, or more skills than can be summarized in one paragraph each, flag this explicitly and use `AskUserQuestion` — question: "This plan is large — should the concept be split into two plugins?", options: "Split into two" / "Keep as one" — cheaper to catch here than after Design.

## Step 3: Allocate Content Depth (Skills Only)

For each planned **skill**, assign a depth tier — reusing this plugin's own existing 80% Rule and category vocabulary (`skill-development/references/skill-workflow.md` Part 1, `skill-development/references/skill-categories.md`), not a new rubric:

| Tier | Structure | When |
|---|---|---|
| **Minimal** | `SKILL.md` only | Core procedural content fits comfortably under ~300 lines; no content is genuinely supplementary (the 80% Rule's "everything stays" case) |
| **Standard** | `SKILL.md` + `references/` | Some content is supplementary (edge cases, advanced config, background) per the 80% Rule's "moves to references/" case |
| **Rich** | `SKILL.md` + `references/` + `scripts/` and/or `assets/` and/or `examples/` | The skill needs executable utilities, output templates, or worked examples beyond prose reference content |

This is a **planning estimate**, not a binding decision — the actual Design skill (`skill-development`) makes the final call per-file using the real 80% Rule during Step 2 (design), since only the actual content reveals what's truly supplementary. Agents and commands don't get a depth tier (single-file components).

## Step 4: Map to Functional Groups

Cluster the planned components into small functional groups (2-5 components each) that share a domain — this keeps the Design phase coherent (design related components together) without inventing a rigid "movement" numbering scheme. Name each group by its domain, not a lifecycle stage (e.g. "Validation reporting," not "Group 3").

## Step 5: Write the Plan

1. Get a timestamp: `date -u +%Y-%m-%dT%H-%M-%SZ`
2. Write to `.claude/output/plugin-planning/<slug>-<timestamp>.md` per `references/plan-template.md`
3. Confirm the written path to the user

## Suggested Next Step

Ask with `AskUserQuestion`: "Proceed to Design for the first functional group, or hand off to `plugin-lifecycle-upstream` to run Design + Build for the whole plan?" — options "Design the first group now" / "Hand off to plugin-lifecycle-upstream" / "Stop here". If the user picks the orchestrator, invoke `plugin-lifecycle-upstream` (via `Skill`) with the written plan path (cycle prevented by `plugin-lifecycle-upstream`'s own Auto-Detection Logic, which skips re-running Phases 1-2 when a Plan path is already given — see that skill's `SKILL.md` for the guard). Never invoke it without asking first.

## Testing & Validation

1. **Concept Card input** — confirm Step 1 reads the full card, not just the name/overlap section
2. **Direct-description input (ideation skipped)** — confirm the written plan notes ideation was skipped
3. **Depth allocation** — construct a concept implying 3 skills of obviously different complexity; confirm each gets a distinct, justified tier, not a uniform default
4. **Code-smell trigger** — construct a concept implying 6 agents; confirm the flow stops and asks about splitting rather than silently proceeding

**Quality gates:**
- [ ] Every planned skill gets an explicit depth tier with a one-clause reason — never left unstated
- [ ] The >4-agent / too-many-skills code-smell check always runs before the plan is written
- [ ] The written plan path is always under `.claude/output/plugin-planning/`
- [ ] The Step 5 handoff offer uses `AskUserQuestion`, never auto-invoked without asking
- [ ] Depth-tier vocabulary matches `skill-workflow.md`'s 80% Rule terms — never introduces a new parallel rubric

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/plan-template.md` | The component-inventory + depth-plan document template used in Step 5 |
| `plugin-ideation` skill | Prior step — produces the Concept Card this skill consumes |
| `plugin-lifecycle-upstream` skill | Next step — orchestrates Design + Build across the planned components |
| `skill-development/references/skill-workflow.md` | The authoritative 80% Rule this skill's depth tiers are built on |
| `skill-development/references/skill-categories.md` | 9 category templates used when deciding a skill's shape |
