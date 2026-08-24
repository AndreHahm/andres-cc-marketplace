# Analysis Type Guide

One paragraph per report-producing skill, reused from each skill's own `SKILL.md` `description`, organized to match Phase 1's two-tier picker.

**Second consumer:** `running-a-full-retrospective`'s own Phase 1 also reads this file, but only the 5 entries under "A single session's component/skill performance", "How agents, tools, or frameworks behaved", and "Rules, conflicts, or recurring issues" — every entry except the 2 under "Compare two things" (`comparing-sessions`, `comparing-session-to-specification`), which take a comparison target rather than a bare scope. Its picker is shaped differently from this file's own two-tier structure, but the same 5 paragraphs serve both.

## A single session's component/skill performance

**`analyzing-plugin-components`** — Analyzes Claude Code sessions from a user-defined start date through today. Executes SWOT analyses, self-critiques, and self-reflections for each skill, sub-agent, command, workflow-skill, and rule active in the session range, reading generated output artifacts in scope and re-verifying their stated open items against current repo state rather than trusting them at face value. With explicit per-instance confirmation, also corrects a non-resolving commit SHA it finds in a re-verified artifact, narrowly scoped to that replacement only. Generates classified improvement suggestions grouped by component and priority. Pick this when the request already names component/skill/agent/rule performance specifically — auditing skill or agent performance, building an improvement backlog, or identifying systemic issues across skills, agents, and rules. A bare, typeless "run a retrospective" or "analyze this session" routes to `starting-an-analysis`'s own Phase 1 instead of landing here directly.

## How agents, tools, or frameworks behaved

**`analyzing-actor-behavior`** — Analyzes agent behavior, human developer behavior, and cross-agent handoff/flow patterns across a session. Assesses how well sub-agents performed (decision quality, consistency, unverifiable-finding rate), what the human developer contributed versus corrected, and how work handed off between multiple agents (sequential delegation, parallel dispatch, nested-call risk). Pick this for auditing how subagents performed, comparing human-vs-agent contribution, or reviewing multi-agent handoffs.

**`analyzing-tool-and-framework-use`** — Inventories external tools actually invoked during a session and auto-detects which developer framework(s) a project uses (GSD, OpenSpec, Speckit, BMAD, GG-SAD, or an unrecognized "other" framework), evaluating role-conformance when a governing-method-plus-execution-companion pairing is detected. Supports a project-level override when auto-detection is ambiguous or absent. Produces tool-use and framework-configuration optimization recommendations. Pick this for a tool-usage inventory or checking whether a project's framework pairing is being used correctly.

## Rules, conflicts, or recurring issues

**`analyzing-governance-and-conflicts`** — Analyzes rule/boundary/convention conformance and detects conflicts — agent-vs-agent, rule-vs-rule, spec-vs-code, and session-vs-session — across a session, plus tracks recurring errors and mistakes. Its session-vs-session check is a single unacknowledged-contradiction flag only, not a full structural/semantic comparison between two sessions (see `comparing-sessions` for that), and not a full multi-report cross-check across several analysis-kit reports from the same scope (see `reviewing-analysis-findings` for that). Reuses the shared `component_inventory.py` script for rule evidence. Pick this for rule/spec conformance questions or spotting conflicts between agents, rules, or a spec and the code.

**`mining-recurring-patterns`** — Mines a session for recurring action sequences and loops, detects recall/memory-consultation gaps, repeated-question patterns, and retry loops, and aggregates whatever subagent-dispatch token/time usage was actually observed — main-conversation-level token/time totals are explicitly out of scope, since no skill can measure those directly. Pick this for finding repeated command patterns, checking whether the same question was asked more than once, or reviewing where subagent time and tokens went.

## Compare two things

**`comparing-sessions`** — Compares two Claude Code sessions structurally, using a deterministic diff over two persisted analysis-kit reports, then interprets what changed semantically — component performance trends, suggestion recurrence, tool/framework detection stability. This is a full structural/semantic comparison, not a single contradiction flag (for that narrower check, see `analyzing-governance-and-conflicts`' session-vs-session conflict category), and not multiple different skills' reports from one shared scope (for that, see `reviewing-analysis-findings`). Pick this to see how a project's session-over-session trends have changed.

**`comparing-session-to-specification`** — Checks whether a session's decisions and actions complied with a project's specification, architecture, constitution, or project-brief document, section by section. Pick this to check whether a session followed its own project's spec, architecture doc, or constitution.
