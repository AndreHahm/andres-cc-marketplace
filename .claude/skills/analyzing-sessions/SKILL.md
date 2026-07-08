---
name: analyzing-sessions
description: >-
  Analyzes Claude Code sessions from a user-defined start date through today. Executes
  SWOT analyses, self-critiques, and self-reflections for each skill, sub-agent, command,
  workflow-skill, and rule active in the session range. Generates classified improvement
  suggestions grouped by component and priority. Use when running a post-session retrospective,
  auditing skill or agent performance, building an improvement backlog, or identifying systemic
  issues across skills, agents, and rules from a session or date range.
allowed-tools: Read Glob Grep Write
---

# Session Analysis

Produce SWOT analyses, self-critiques, and improvement suggestions for every component used across a session range.

## Quick Start

1. Choose scope — "This conversation" for the current session, or provide a start date for a date range.
2. Confirm the Phase 2 component inventory before the analysis runs.
3. Skim SWOT + critique output in P1 → P3 priority order.
4. Act on the **Top 5 Actions** from Phase 6.

For date-range retrospectives or deep taxonomy guidance, read the full phases below.

## When to Use

- Post-session retrospective after completing a development task
- Auditing how skills, sub-agents, commands, or rules performed during a session
- Building an improvement backlog from multiple observed failures
- After acting on improvement suggestions that affect skill behavior, validate the fix using `skill-tester` — `skill-evaluation-protocol` governs the evaluation criteria
- Identifying systemic issues that span more than one component
- Any session involving: skills · sub-agents · commands · workflow-skills · rules

## When NOT to Use

- **Real-time monitoring** — this skill is retrospective; it analyzes past behavior, not live state
- **No `.claude/` components were active** — if no skills, agents, commands, or rules were involved, there is nothing to analyze
- **Single-component review** — use `skill-reviewer` for one skill or `plugin-validator` for one plugin; this skill adds overhead without benefit for isolated reviews
- **Code quality** — use `/code-review` for diff analysis; this skill covers skill and agent behavior, not code correctness

## Phase 1: Scope

If a scope was supplied as an argument (a date string, `"today"`, `"this conversation"`, or similar), skip the question UI and proceed directly to Phase 2 using that argument as the scope.

Ask for the session range only when no argument was provided:

```
questions: [
  {
    question: "What should this analysis cover?",
    header: "Session scope",
    options: [
      { label: "This conversation", description: "Analyze only the current conversation context" },
      { label: "From a start date", description: "Provide a YYYY-MM-DD start date; analysis runs through today" },
      { label: "Today", description: "All sessions from today (default)" }
    ],
    multiSelect: false
  }
]
```

If "From a start date" → ask for the date. If sessions from prior conversations are in scope, ask the user to paste in relevant transcript excerpts or summaries — Claude cannot read past conversation history directly.

## Phase 2: Component Inventory

**Run these Globs first, unconditionally — before evaluating scope or waiting for confirmation:**
- `Glob(pattern='*', path='.claude/output')` — output artifacts from prior runs
- `Glob(pattern='*.md', path='.claude/rules')` — rules that load automatically, often without being mentioned in conversation

**Use the `path` parameter form above, not a bare relative pattern like `Glob('.claude/rules/*.md')`** — on at least one observed environment, a pattern with a literal leading `.claude/` segment silently returned no results even though matching files existed, while pointing `path` directly at the target directory with a bare pattern resolved correctly. A silent false negative here means rules or prior output artifacts go uncounted without any visible error, so treat an empty result from either call as suspect: retry once with a broader pattern (e.g. `Glob(pattern='**/*', path='.claude/rules')`) before concluding the category is genuinely empty.

These seed the inventory regardless of scope. Then identify every additional component from the current conversation context.

| Category | What counts |
|---|---|
| **Skill** | Slash-command invocations that loaded a `SKILL.md` (e.g. `/skill-refiner-interactive`) — **or** a skill's `SKILL.md`/`references/*.md`/`scripts/*` files that were directly edited this session, even without an invocation event (see note below) |
| **Sub-agent** | Agent tool spawns (named agent type or description used) |
| **Command** | `.claude/commands/*.md` invocations |
| **Workflow-skill** | Skills invoked as sub-steps inside another skill's workflow |
| **Rule** | `.claude/rules/*.md` files loaded and applied during the session |

**Invoked vs. edited components:** both count, and both get their own SWOT — but frame them differently. An *invoked* component is assessed on how well it performed when run (did its checks fire, did its output need correction). An *edited* component (one whose files you modified as a task, without ever loading it via `Skill`/`Agent`) is assessed on how well its existing structure/docs supported making that edit correctly, and what defects the edit surfaced. Don't skip edited components just because there's no invocation event to point to as evidence — the edit itself is the evidence.

Emit the inventory before proceeding:

```
📦 Session Inventory  <start> → <end>
| # | Component | Category | Evidence |
```

Confirm: "Found N components. Proceed with full analysis?"

## Phase 3: SWOT Analysis

For each component, produce a SWOT grounded in observed session behavior — not design intent.

```
### SWOT: <name>  (<category>)
| Quadrant     | Observations |
| Strengths    | … |
| Weaknesses   | … |
| Opportunities| … |
| Threats      | … |
```

See `references/swot-framework.md` for quadrant prompts and common patterns per component category.

## Phase 4: Self-Critique and Self-Reflection

For each component, immediately after its SWOT:

**Self-Critique** — what went wrong:
- Errors, omissions, wrong assumptions made during execution
- Checklist items skipped or gates bypassed
- Output produced that should not have been

**Self-Reflection** — what would change:
- Alternative approach that would produce better results next time
- Cross-component patterns pointing to a systemic issue
- Meta-lessons that apply beyond this specific component

See `references/critique-reflection-framework.md` for question sets by category and rationalizations to reject.

## Phase 5: Generate and Classify Suggestions

Derive one or more concrete suggestions from each SWOT entry and each critique/reflection point. Discard observations with no actionable change. Merge duplicate suggestions across components into one cross-cutting entry.

Each suggestion:
```
[S##] [P1|P2|P3] [TYPE]  <one-line description>
Source: <SWOT quadrant | Critique | Reflection>   Component: <name>
Detail: <what to change and why>
```

Priority: **P1 Critical** (breaks behavior), **P2 Major** (degrades quality), **P3 Minor** (polish).
Types: `FIX` · `ENHANCE` · `ADD` · `REMOVE` · `AUDIT`

See `references/suggestion-taxonomy.md` for classification rules, merge criteria, and examples.

## Phase 6: Grouped Report

Output two views.

**By component** — each component with its suggestions in P1→P3 order:
```
## <name>  (<category>)
[S01] P1 FIX    …
[S02] P2 ADD    …
```

**By classification** — all suggestions across components by priority then type:
```
### P1 — Critical
[S01] skill-reviewer · FIX  …
### P2 — Major
…
### P3 — Minor
<details><summary>N minor suggestions</summary>…</details>
```

Close with **Top 5 Actions**: the five highest-impact suggestions across all components, in order.

## Testing & Validation

After Phase 6, verify these gates before presenting output as final:

- [ ] Inventory names at least one component per category present in the session
- [ ] Every SWOT quadrant has at least one observation (no empty rows)
- [ ] Every P1 suggestion names a specific file, section, or step in its Detail field
- [ ] Top 5 Actions are drawn from P1 first; P2 entries appear only when no P1 remain
- [ ] No two suggestions share the same Detail description — merge duplicates before emitting

## Gotchas

- **Absence of evidence ≠ absence of use.** Rules in `.claude/rules/` load automatically — check the directory even if they were never mentioned in conversation.
- **Weakness vs. Threat confusion.** Weaknesses are internal to the component (a missing gate, a wrong threshold). Threats are external (a stale dependency, an upstream change that will break the component). Do not cross-file them.
- **Over-suggestion.** Not every observation earns a suggestion. If two components produced the same fixable pattern, emit one cross-cutting suggestion, not two identical ones.
- **Prior-session data.** Claude cannot read past conversation history. For sessions before the current one, prompt the user to paste transcripts or summaries before Phase 2.
- **Self-referential sessions.** When `analyzing-sessions` is itself one of the components being analyzed, the assessment is inherently limited — the skill cannot objectively observe its own execution from outside. Note this explicitly in the SWOT weakness quadrant rather than producing inflated self-assessments.

## Reference Guide

| File | Purpose | When to read |
|---|---|---|
| `references/swot-framework.md` | Quadrant prompts and category-specific patterns | Phase 3 |
| `references/critique-reflection-framework.md` | Question sets per category; rationalizations to reject | Phase 4 |
| `references/suggestion-taxonomy.md` | Priority tiers, type definitions, merge rules, examples | Phase 5 |
