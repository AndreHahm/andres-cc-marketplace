---
name: component-prototyping
description: >-
  Try running a new skill, agent, or hook idea locally before it's a committed plugin
  component -- without installing it into .claude/skills/, polluting the live component
  set, or needing a separate `cc --plugin-dir` session. Use when prototyping a new
  component idea, "let me try this skill before I build it for real", "test this agent
  idea", "run this hook script against sample input", or iterating on a component that
  isn't ready to belong to any plugin yet.
allowed-tools: Read Write Glob Agent Bash(python:*) Bash(node:*) AskUserQuestion
---

# Component Prototyping

Try a skill, agent, or hook idea by running it against a sample scenario — without it ever being live in `.claude/skills/`, `.claude/agents/`, or any plugin. The experiment stays in a gitignored scratch directory the whole time; nothing here makes it discoverable or invocable by name.

## Where experiments live

`.experiments/<component-name>/` at the repo root — gitignored (`**/.experiments/`), separate from `.draft/` (which holds whole draft *plugins*, not single loose components). Shape matches the real component type:

- **Skill**: `.experiments/<name>/SKILL.md` (+ optional `references/*.md`)
- **Agent**: `.experiments/<name>.md` (a single file, agent-style frontmatter)
- **Hook**: `.experiments/<name>/hooks.json` + its backing script (`.py`/`.js`/`.sh`)

## Workflow

1. **Resolve the target.** `Glob('.experiments/**')` to find existing experiments. If none exist, or the user describes a new idea, scaffold the experiment from what they describe — write the SKILL.md/agent file/hook script directly, don't ask permission to create files inside `.experiments/` (it's a scratch space, not a live component).
2. **Identify the type**: a directory with `SKILL.md` is a skill; a single `.md` file with agent-style frontmatter (`name`, `description`, optionally `tools`/`model`) is an agent; a directory with `hooks.json` or a bare script is a hook.
3. **Skill or agent — dispatch a blind trial run.** Get a sample scenario (ask via `AskUserQuestion` if the user hasn't already given one). Read the component's full raw content, then dispatch one `Agent` call, type `general-purpose`, with a prompt structured like:

   ```
   You are testing a Claude Code [skill/agent] that does not exist as a real component yet.
   Follow the instructions below exactly, as if they were your own skill/agent definition.

   [SKILL/AGENT DEFINITION]:
   <full raw content of the experiment file>

   SCENARIO:
   <the sample input/task>

   Do the work the instructions describe. Report what you did and produced.
   ```

   This reuses `skill-tester`'s own blind-content pattern (see its `references/eval-schema.md` "WITH_SKILL_ONLY Template") — same mechanism, lighter purpose: one quick trial, not a formal benchmark. No `evals.json`, no workspace directory, no baseline comparison.
4. **Hook — run directly or hand off.** For a Python or Node hook script, run it directly (`Bash(python:*)`/`Bash(node:*)`) with representative event JSON piped via stdin, matching how Claude Code actually invokes hooks; show stdout/stderr/exit code. For a Bash hook script, don't execute it directly — a general shell-interpreter grant is exactly what `plugin-rulebook`'s R6 forbids, experiment or not. Instead, print the exact command the user can run themselves (`bash .experiments/<name>/script.sh <<< '<sample-json>'`).
5. **Present the trial run plainly** — what the subagent did, what it produced, whether it matched intent. This is a read of behavior, not a verdict; the user judges whether it's close enough to keep going.
6. **Iterate or stop.** If the user wants to keep going, edit the experiment file directly, then ask via `AskUserQuestion` before dispatching another trial run — never loop silently (R26: each trial is a real LLM-cost dispatch, opt in per round, not just on the first one).
7. **Promote, when ready.** This skill doesn't scaffold plugins itself — hand off to the right existing tool once the user is satisfied: `plugin-ideation`/`plugin-development` if the experiment is the seed of a new plugin, or moving the file directly into an existing `.draft/<plugin-name>/` folder if it belongs to a plugin already being drafted. State which path applies; don't execute the move without confirming first.

## Boundaries

- **Not a replacement for `skill-tester`.** `skill-tester` runs formal A/B benchmarks (with-skill vs. baseline, timing/token metrics, persisted `evals/`) against a *real, installed* skill. This skill is for the step before that exists at all — a single "does this roughly do what I mean" check on something that isn't installed anywhere.
- **Not a replacement for `require-tests-for-behavior-changes.md`'s gate.** That rule governs behavior changes to real, shipped components. An experiment isn't shipped yet, so it doesn't trigger that gate — the gate applies once the experiment graduates and becomes a real component whose behavior might later change.
- **Never writes outside `.experiments/`** during the trial-and-iterate loop. Promotion (step 7) is the only point files leave the scratch directory, and only with explicit confirmation.
