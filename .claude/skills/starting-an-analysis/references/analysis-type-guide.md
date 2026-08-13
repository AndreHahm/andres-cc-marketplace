# Analysis Type Guide

One paragraph per report-producing skill, reused from each skill's own `SKILL.md` `description`, organized to match Phase 1's two-tier picker.

## A single session's component/skill performance

**`analyzing-plugin-components`** — Analyzes Claude Code sessions from a user-defined start date through today. Executes SWOT analyses, self-critiques, and self-reflections for each skill, sub-agent, command, workflow-skill, and rule active in the session range, reading generated output artifacts in scope and re-verifying their stated open items against current repo state rather than trusting them at face value. Generates classified improvement suggestions grouped by component and priority. Pick this for a general post-session retrospective, auditing skill or agent performance, building an improvement backlog, or identifying systemic issues across skills, agents, and rules.

## How agents, tools, or frameworks behaved

**`analyzing-actor-behavior`** — Analyzes agent behavior, human developer behavior, and cross-agent handoff/flow patterns across a session. Assesses how well sub-agents performed (decision quality, consistency, unverifiable-finding rate), what the human developer contributed versus corrected, and how work handed off between multiple agents (sequential delegation, parallel dispatch, nested-call risk). Pick this for auditing how subagents performed, comparing human-vs-agent contribution, or reviewing multi-agent handoffs.

**`analyzing-tool-and-framework-use`** — Inventories external tools actually invoked during a session and auto-detects which developer framework(s) a project uses (GSD, OpenSpec, Speckit, BMAD, GG-SAD, or an unrecognized "other" framework), evaluating role-conformance when a governing-method-plus-execution-companion pairing is detected. Produces tool-use and framework-configuration optimization recommendations. Pick this for a tool-usage inventory or checking whether a project's framework pairing is being used correctly.

## Rules, conflicts, or recurring issues

**`analyzing-governance-and-conflicts`** — Analyzes rule/boundary/convention conformance and detects conflicts — agent-vs-agent, rule-vs-rule, spec-vs-code, and session-vs-session — across a session, plus tracks recurring errors and mistakes. Its session-vs-session check is a single unacknowledged-contradiction flag only, not a full comparison (see `comparing-sessions` for that). Pick this for rule/spec conformance questions or spotting conflicts between agents, rules, or a spec and the code.

**`mining-recurring-patterns`** — Mines a session for recurring action sequences and loops, detects recall/memory-consultation gaps, repeated-question patterns, and retry loops, and aggregates whatever subagent-dispatch token/time usage was actually observed. Pick this for finding repeated command patterns, checking whether the same question was asked more than once, or reviewing where subagent time and tokens went.

## Compare two things

**`comparing-sessions`** — Compares two Claude Code sessions structurally, using a deterministic diff over two persisted analysis-kit reports, then interprets what changed semantically — component performance trends, suggestion recurrence, tool/framework detection stability. This is a full structural/semantic comparison, not a single contradiction flag. Pick this to see how a project's session-over-session trends have changed.

**`comparing-session-to-specification`** — Checks whether a session's decisions and actions complied with a project's specification, architecture, constitution, or project-brief document, section by section. Pick this to check whether a session followed its own project's spec, architecture doc, or constitution.
