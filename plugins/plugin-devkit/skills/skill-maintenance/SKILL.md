---
name: skill-maintenance
description: >-
  Decide whether and how to update plugin-devkit components — skills, agents,
  commands, hooks, or rules — after finishing other work in this plugin.
  Use after completing a feature, adopting a new convention, discovering a
  pattern or anti-pattern worth documenting, or changing a canonical value
  (e.g. a settings.json enum or threshold). Not for every commit — only
  changes that affect how a component should behave. Routes the actual
  edit to skill-development, agent-development, command-development,
  hook-development, or rule-development, then to plugin-rulebook for
  compliance and to skill-reviewer, subagent-reviewer, command-reviewer,
  hook-reviewer, rule-reviewer, consistency-reviewer, or plugin-validator
  for verification.
allowed-tools: Read Grep Glob Skill Agent
---

# Skill Maintenance

Decision guide for whether a change in this plugin should propagate into an update of a skill, agent, command, hook, or rule — and, if so, which sibling component owns the edit and which owns the verification. This skill decides and routes; it never edits a component directly.

## Core Principle: Balanced Updates

Plugin-devkit components should stay current but not churn on every commit. Update a component only for **meaningful changes** that affect how a future agent or developer should work with it.

## When to Use

- Right after finishing a feature, fix, or exploration in this plugin, to check whether the work revealed something worth documenting
- After discovering a new pattern, anti-pattern, or convention during development (e.g. the `per_agent_extensions` pattern discovered this session for reviewer-agent action enums)
- After changing a canonical value that other components reference (a `settings.json` enum, threshold, or forbidden-field list)
- When unsure which sibling skill/agent should own an update you already know is needed

## When NOT to Use

- **Periodic, library-wide freshness/overlap auditing, not tied to a specific change** — use `skill-stocktake` instead; that skill's Full/Quick Scan modes are the right tool for "is anything stale across the whole collection," this skill only covers change-triggered updates
- **Retrospective analysis of how components performed across a session** — use `analyzing-sessions` instead
- **Structural/naming/formatting compliance checking** — use `plugin-rulebook` directly; this skill tells you a rulebook check is owed, it doesn't perform one
- **Actually writing or editing a component's content** — use the matching `*-development` skill (this skill routes to it, but doesn't do the edit itself)
- **A component that doesn't exist yet** — that's plain creation, not maintenance; go straight to the matching `*-development` skill

## Step 1: Classify the Change

| Update | Don't update |
|---|---|
| New convention adopted (e.g. a shared enum, a new field pattern) | Bug fix that doesn't reveal a pattern |
| New pattern discovered worth documenting as a Gotcha or reference | Small, self-contained feature addition |
| New anti-pattern discovered (something that broke, was flagged, or was corrected) | Refactor that doesn't change behavior or guidance |
| Canonical value changed (settings.json enum, threshold, forbidden-field list — see R20) | Formatting, renaming, or comment-only changes |
| A component's interface/behavior changed in a way siblings assume | Work still in `.temp/to-implement/` or `.draft` — not shipped, not yet a maintenance concern |
| A critical constraint or new REQUIRED rule was added | Documentation-only edits with no behavioral claim |

If nothing in the left column applies, stop here — no update needed.

## Step 2: Identify Affected Components

Ask: "Which components reference this fact, pattern, or convention?"

- **Canonical-value changes** (settings.json enums, thresholds, field lists): this is exactly `plugin-rulebook`'s R20 Duplicate Fact Sweep — grep the plugin tree for the old value and list every sibling file that still references it.
- **Pattern/convention/anti-pattern discoveries** (no single canonical source to grep for the old value): grep for the concept's name or the closest existing terminology across `plugins/plugin-devkit/**/*.md`, then check whether any `*-development` skill's reference files, or any `*-reviewer` agent's checklist, should mention it.
- **Interface/behavior changes**: check every component that names the changed component by file path or by name in prose — a stale cross-reference is worse than a missing one, since it actively misleads.

## Step 3: Route the Update

| Component type | Edit via | Verify via |
|---|---|---|
| Skill | `skill-development` (Audit entry path) | `skill-reviewer` agent |
| Agent | `agent-development` | `subagent-reviewer` agent |
| Command | `command-development` | `command-reviewer` agent |
| Hook | `hook-development` | `hook-reviewer` agent |
| Rule (`.claude/rules/*.md`) | `rule-development` | `rule-reviewer` agent |

Every edit still ends at `plugin-rulebook` before finalizing, per `.claude/rules/plugin-rulebook-enforcement.md` — that gate is mandatory and not optional regardless of which row above applies; this skill only tells you the edit is owed, the matching `*-development` skill is what actually invokes the compliance check as its own last step.

## Step 4: Make Minimal Changes

- Add the new information; don't rewrite unrelated existing content
- Match the target component's existing structure and voice
- If the change is a discovered anti-pattern, prefer adding a Gotcha-style entry (problem + fix) over a long prose explanation — this plugin's own `*-development` skills already use that convention
- If the plugin's `.claude/` staging mirror applies to the target (see R19's in-development-mirror exception), remember both copies need the edit — not just the canonical `plugins/plugin-devkit/` one

## Step 5: Verify

1. **Component-level quality** — run the matching `*-reviewer` agent from Step 3's table (via `Agent`) against the edited component
2. **Rulebook compliance** — run `plugin-rulebook` (via `Skill`) against the edited component; this is mandatory before the change is considered finalized, not optional
3. **Cross-component consistency** — if more than one sibling component was touched, or if Step 2 found other components that reference the same fact but weren't edited, that's exactly `consistency-reviewer`'s job — flag it as a candidate rather than skipping it
4. **Whole-plugin wiring** — if a component was newly created (not just edited), run `plugin-validator` (via `Agent`) to confirm it's correctly wired into the plugin's directory structure and manifest

If Step 2 found affected components beyond the one already edited, ask before touching them:

```
question: "This change also affects [component list] — update those too?"
header: "Cascading update"
options:
  - label: "Yes — update all"
    description: "Apply the same change to every affected component now"
  - label: "No — just this one"
    description: "Leave the others as-is; note the drift for a future pass"
```

Never cascade an edit to a sibling component without this confirmation — an unreviewed change to a component the user didn't ask about is a bigger risk than leaving a documented gap.

## Update Checklist

Before considering a maintenance update complete:

- [ ] Classified as Update, not Don't-update (Step 1)
- [ ] All affected components identified, not just the first one found (Step 2)
- [ ] Edit routed through the matching `*-development` skill, not hand-edited ad hoc (Step 3)
- [ ] Change is minimal — no unrelated rewrites (Step 4)
- [ ] Matching `*-reviewer` agent run against the edit (Step 5.1)
- [ ] `plugin-rulebook` run and passing (Step 5.2)
- [ ] Cross-component drift checked if multiple components were touched (Step 5.3)
- [ ] `.claude/` mirror re-synced if the target has one (Step 4)

## Staleness Signals (When to Suggest a Broader Audit, Not an Update)

If a maintenance check surfaces signs the problem is bigger than one component — several siblings reference the same stale fact, or a component hasn't been touched in a long time and its references look outdated — that's a signal to recommend `skill-stocktake`'s Full Stocktake, not to try to fix everything inline here. This skill handles one change at a time; broader drift belongs to the periodic audit tool.

## Commit Message Convention

This repo's convention (see recent `git log`): a short, imperative-mood summary line (what changed, not "fixed" or "updated"), an optional body explaining the WHAT/WHY when the change isn't self-evident from the title, and a trailing `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` line. Scope prefixes like `docs(skills):` are not this repo's convention — don't introduce one.

## Testing & Validation

After using this skill to route a change, verify:

1. **Correct routing** — the edit landed in the component type Step 3 said it should (a pattern discovered in agent behavior didn't get written into a skill's SKILL.md instead of the relevant agent file)
2. **No skipped verification** — Step 5.1 and 5.2 both ran; a maintenance update that skips `plugin-rulebook` is incomplete regardless of how small the edit was
3. **Cascading gate respected** — if Step 2 found more than one affected component, the `AskUserQuestion` gate in Step 5 was used, not a silent multi-component edit

**Quality gates:**
- [ ] Never edits a component directly — always routes to the matching `*-development` skill
- [ ] Never cascades to a second component without the Step 5 `AskUserQuestion` gate
- [ ] Never substitutes for `plugin-rulebook` — always names it as the mandatory finishing step, never skips or inlines its checks

## Reference Guide

| Resource | Purpose |
|---|---|
| `skill-development` | Owns skill creation/editing; Audit entry path is the update mechanism for skills |
| `agent-development` | Owns agent creation/editing |
| `command-development` | Owns command creation/editing |
| `hook-development` | Owns hook creation/editing |
| `rule-development` | Owns `.claude/rules/*.md` creation/editing |
| `plugin-rulebook` | Mandatory structural/naming/formatting/tool-scoping compliance gate before any update is final |
| `skill-reviewer` / `subagent-reviewer` / `command-reviewer` / `hook-reviewer` / `rule-reviewer` agents | Component-level quality verification after an edit |
| `consistency-reviewer` agent | Cross-component drift check when multiple siblings reference the same fact |
| `plugin-validator` agent | Whole-plugin structural/wiring validation after a new component is added |
| `skill-stocktake` | Periodic, library-wide freshness/overlap audit — not for single-change routing |
| `.claude/rules/plugin-rulebook-enforcement.md` | The project rule that makes the Step 5.2 compliance gate mandatory, not advisory |
