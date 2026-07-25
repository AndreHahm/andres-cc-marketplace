---
name: plugin-ideation
description: >-
  Brainstorms a new Claude Code plugin or plugin component from a rough idea or problem
  statement — checks for overlap against existing plugins, proposes kebab-case name
  candidates, and estimates a complexity tier. Use when the user asks to "brainstorm a
  plugin idea", "ideate a plugin", "what should I build", "propose a name for a plugin",
  "check if a plugin like X already exists", or describes a rough problem they want a
  plugin or new skill/agent/command to solve, without yet having a concrete design.
  Produces a Concept Card, not a design or implementation — see plugin-planning for the
  next step.
argument-hint: "[rough idea or problem statement]"
allowed-tools: Read Glob Grep Write Bash(date:*) Skill
---

# Plugin Ideation

Brainstorms and refines a rough idea into a validated concept through an actual back-and-forth with the user — not a background computation that surfaces only at the end. This is the first step of the upstream lifecycle; `plugin-planning` picks up from here.

**Ideation is an interview, not a report generator.** Every step through Step 4 involves the user directly via `AskUserQuestion` — asking, listening, refining, asking again. Nothing gets locked in silently. If you catch yourself computing several steps in a row before showing the user anything, stop — that's the anti-pattern this skill exists to avoid.

## Quick Start

1. **Determine scope** — whole new plugin, or a new component inside an existing plugin? (Step 1)
2. **Interview the user** — brainstorm and refine the problem, audience, and boundaries through actual dialogue, not a one-shot confirm (Step 2)
3. **Check for overlap, then discuss it** — search existing coverage, then bring findings back to the user for reaction (Step 3)
4. **Propose names, then let the user choose** — 3-5 kebab-case candidates presented as a live decision, not a unilateral pick (Step 4)
5. **Estimate complexity** — a rough size tier from the refined concept (Step 5, background — genuinely just an estimate)
6. **Write the Concept Card** — `.claude/output/plugin-ideation/<slug>-<timestamp>.md`, only after Steps 2-4 are settled (Step 6)

## When to Use

- The user has a rough idea or problem statement but no concrete design yet
- Before starting `plugin-planning` or `plugin-development`'s New Plugin Creation Interview
- Checking whether a proposed plugin or component idea already exists somewhere installed or in this repo
- Naming a new plugin or component and validating the name is available and rule-compliant

## When NOT to Use

- The user already has a concrete design (components, triggers, scope decided) — go straight to `plugin-planning` or the relevant Design skill (`skill-development`, `agent-development`, `command-development`, `hook-development`, `rule-development`)
- Reviewing or scoring an *existing* plugin's quality — use `plugin-grader` instead
- Comparing two already-identified plugins/components side-by-side — use `plugin-comparison` instead
- Scaffolding plugin files — use `plugin-development`; ideation produces a concept, not files
- Wanting the full guided Ideate→Plan→Design→Build pipeline rather than just this step — use `plugin-lifecycle-upstream` instead (it dispatches here automatically)

## Step 1: Determine Scope

Ask (unless already clear from the request): is this a **whole new plugin**, or a **new component** (skill/agent/command/hook) inside an existing plugin (this repo's `plugin-dev`, or another plugin the user names)?

This determines which Concept Card template applies (Step 6) and narrows the overlap search in Step 3.

## Step 2: Interview the User

This is brainstorming, not intake — even a detailed `$ARGUMENTS` gets at least one real round of dialogue before moving on. Never skip straight to Step 3 on the reasoning that "the idea already answers this."

Use `AskUserQuestion` for each round — free-form ("Other") answers are expected and normal here, this is not a multiple-choice form:

1. **Problem round:** What problem does this solve? What's missing today? If `$ARGUMENTS` already states a problem, reflect it back and ask an open refining question ("Is it specifically X, or does it also need to cover Y?") rather than just restating it as confirmed.
2. **Audience round:** Who uses it, and in what situation? Push for a concrete scenario, not a role label — "a developer" is not an answer, "someone mid-session who just built a component and wants to hand it off" is.
3. **Boundary round:** What should this explicitly *not* do? Any existing plugin, skill, or tool this resembles or should differ from? This round surfaces scope creep early, before Step 3's overlap search even runs.

After each round, briefly reflect what you heard and ask if anything's missing or wrong — don't just move to the next round. If the user's answer opens a new question (a new edge case, a boundary they didn't think of), follow it before proceeding to Step 3. Stop the interview when the user signals they're ready to move on ("that's it", "sounds right", "let's continue") — not on a fixed question count.

## Step 3: Check for Overlap, Then Discuss It

Search for existing coverage before proposing anything new:

- **This repo's plugins**: `Glob('**/.claude-plugin/plugin.json')` and `Glob('**/SKILL.md')` — read `name`/`description` of each match
- **Installed plugins**: `Read('~/.claude/plugins/installed_plugins.json')` if present (same resolution `plugin-comparison` Step 2 uses)
- **Component scope only**: also check the target plugin's own `agents/*.md` and `commands/*.md` for name/description collisions

Classify the result, then **bring it back to the user** — do not just silently record the classification and move on:

| Overlap | Meaning | Action |
|---|---|---|
| **None** | No existing component covers this problem | State this plainly and proceed to Step 4 — no need for a full `AskUserQuestion` round here, a brief confirmation in prose is enough |
| **Partial** | Something adjacent exists but doesn't fully cover the idea | Present the adjacent component(s) and the proposed boundary to the user via `AskUserQuestion` ("this exists and is adjacent — does the boundary I'm proposing sound right, or should the scope shift?") before proceeding. This is where scope actually gets refined — treat it as part of the brainstorm, not a formality |
| **Full** | An existing component already does this | Stop. Tell the user which component already covers it and ask whether they want to extend that instead of ideating a duplicate |

## Step 4: Propose Names, Then Let the User Choose

Generate 3-5 kebab-case candidates. Each candidate MUST:

- Match `^[a-z][a-z0-9-]+[a-z0-9]$` (plugin-rulebook R4), 3-64 chars
- Not contain `anthropic` or `claude`
- Not collide with any name found in Step 3's search

Prefer names that state the domain, not the mechanism (`skill-tester` not `evaluation-runner-thing`) — mirrors this plugin's own naming pattern.

Present the candidates via `AskUserQuestion` and let the user pick — do not unilaterally declare one "preferred" and move on. If the user's request already named the component, include that name as one of the candidates rather than overriding it, and say explicitly why the other candidates might be worth considering instead (or confirm the given name is already the best fit).

## Step 5: Estimate Complexity

A rough size tier from the described scope — informational only, refined properly by `plugin-planning`:

| Tier | Component count | Typical scope |
|---|---|---|
| **Small** | 1-3 | A single focused skill or agent |
| **Medium** | 4-8 | A few related skills, maybe one agent |
| **Large** | 9+ | Multiple skills, agents, possibly hooks — consider whether this should be two plugins |

If the estimate lands in **Large** and the idea spans genuinely unrelated domains, say so explicitly and suggest splitting before proceeding — cheaper to catch here than after `plugin-planning`.

## Step 6: Write the Concept Card

1. Get a timestamp: `date -u +%Y-%m-%dT%H-%M-%SZ`
2. Write to `.claude/output/plugin-ideation/<slug>-<timestamp>.md` using the template in `references/concept-card-template.md` (separate templates for whole-plugin vs. component scope — read the file to pick the right one per Step 1's answer)
3. Confirm the written path to the user

## Suggested Next Step

If the Concept Card's overlap classification is **None** or **Partial**, ask with `AskUserQuestion`: "Proceed to `plugin-planning` to turn this concept into a component inventory?" — options "Yes — run plugin-planning" / "No — stop here". If yes, invoke the `plugin-planning` skill (via `Skill`) with the written Concept Card path. Never invoke it without asking first.

## Testing & Validation

1. **Detailed `$ARGUMENTS` given** — confirm Step 2 still runs at least one real interview round via `AskUserQuestion` rather than skipping straight to Step 3 because the description "already answers it"
2. **Whole-plugin idea** — confirm the skill asks scope first, then produces a Concept Card with all required sections filled (no placeholder text left in)
3. **Component idea inside an existing plugin** — confirm the overlap search checks that plugin's own `agents/`/`commands/`/`skills/`, not just the whole-repo search
4. **Full overlap detected** — confirm the skill stops and names the existing component rather than proposing a duplicate
5. **Partial overlap detected** — confirm the finding is presented to the user via `AskUserQuestion` for reaction before Step 4, not just recorded silently in the Concept Card
6. **Name collision** — construct a case where a proposed candidate collides with an existing plugin name; confirm it's excluded from the final candidate list
7. **Name candidates presented** — confirm the user picks via `AskUserQuestion` rather than the skill unilaterally declaring a "preferred" candidate

**Quality gates:**
- [ ] Step 2 always runs at least one interview round via `AskUserQuestion`, even when `$ARGUMENTS` is detailed — never shortcuts to "summarize and confirm"
- [ ] Overlap search always runs before name candidates are proposed — never skipped
- [ ] A Partial overlap finding is always surfaced to the user for reaction before Step 4 — never only recorded in the final card
- [ ] Every proposed name passes the R4 kebab-case pattern before being shown to the user
- [ ] Name selection is a user decision via `AskUserQuestion`, never a unilateral pick by the skill
- [ ] Full overlap always stops the flow and asks the user, never silently proceeds
- [ ] The Concept Card is written (Step 6) only after Steps 2-4 are settled with the user — never drafted as a fait accompli and shown for the first time at the final gate
- [ ] The Concept Card path is always under `.claude/output/plugin-ideation/`
- [ ] The Step 6 handoff offer uses `AskUserQuestion`, never auto-invoked without asking

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/concept-card-template.md` | The two Concept Card templates (whole-plugin, component) used in Step 6 |
| `plugin-planning` skill | Next step — turns an accepted Concept Card into a component inventory and content-depth plan |
| `plugin-comparison` skill | Reused installed-plugin resolution pattern (Step 3) |
| `plugin-rulebook` R4 | Naming pattern validated in Step 4 |
