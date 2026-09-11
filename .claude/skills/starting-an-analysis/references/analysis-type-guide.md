# Analysis Type Guide

One paragraph per report-producing "analysis type" skill, reused from each skill's own `SKILL.md`
`description`, organized into 4 sections matching Phase 1's Tier-1/Tier-2 picker.

**Second consumer:** `running-a-full-retrospective`'s own Phase 1 also reads this file, but only the 11
entries under "Outcome, verification & operational reliability," "Component, tool & actor performance,"
"Usability, governance & security," and the first 2 entries under "Patterns, opportunities & comparisons"
(`mining-recurring-patterns`, `identifying-feature-opportunities`) — never the last 2 entries under that
same section (`comparing-sessions`, `comparing-session-to-specification`), which take a comparison target
rather than a bare scope and don't fit that skill's own shared-scope multi-select. Its picker is shaped
differently from this file's own two-tier structure (a 4-question multi-select split, not a Tier-1/Tier-2
single-select), but the same 11 paragraphs serve both.

## Outcome, verification & operational reliability

**`analyzing-session-outcomes`** — Analyzes whether a Claude Code session achieved the user's actual goal
and any explicit acceptance criteria -- not merely whether the process was followed. Builds a Goal
Inventory from the highest available evidence tier, assigns each goal or criterion a
met/partially_met/not_met/not_verifiable verdict, and separates task completion from process compliance
in the report itself. Pick this when checking whether a session actually accomplished what was asked,
auditing acceptance-criteria attainment, or judging user-visible value delivered versus scope left
unresolved.

**`analyzing-verification-effectiveness`** — Evaluates whether claimed verification -- tests, checks,
manual trials -- was actually proportionate, adequate evidence for the behavior and risk changed, not
just whether "tests were run." Classifies each claim into missing/weak/failed/skipped/false_negative/
unverified_claim/adequate, and requires an exact verification command or evidence citation before
recommending a finding be closed. Never accepts a commit message as proof a test passed. Pick this when
checking whether a fix or change was actually verified adequately, auditing test coverage against risk,
or investigating a defect that escaped despite claimed testing.

**`analyzing-session-operations`** — Analyzes a Claude Code session's operational reliability (failures,
retries, recovery, recurrence) and performance/cost (latency, tokens, critical path, parallelism) as two
distinct report sections sharing one coverage preamble, with every denominator disclosed rather than
estimated when evidence is missing. Pick this when checking how reliably a session ran, why a failure
recurred, whether retries actually recovered, or where latency/token cost actually went and whether
parallelism was used effectively.

## Component, tool & actor performance

**`analyzing-plugin-components`** — Analyzes Claude Code sessions from a user-defined start date through today. Executes SWOT analyses, self-critiques, and self-reflections for each skill, sub-agent, command, workflow-skill, and rule active in the session range, reading generated output artifacts in scope and re-verifying their stated open items against current repo state rather than trusting them at face value. With explicit per-instance confirmation, also corrects a non-resolving commit SHA it finds in a re-verified artifact, narrowly scoped to that replacement only. Generates classified improvement suggestions grouped by component and priority. Pick this when the request already names component/skill/agent/rule performance specifically — auditing skill or agent performance, building an improvement backlog, or identifying systemic issues across skills, agents, and rules. A bare, typeless "run a retrospective" or "analyze this session" routes to `starting-an-analysis`'s own Phase 1 instead of landing here directly.

**`analyzing-actor-behavior`** — Analyzes agent behavior, human developer behavior, and cross-agent handoff/flow patterns across a session. Assesses how well sub-agents performed (decision quality, consistency, unverifiable-finding rate), what the human developer contributed versus corrected, and how work handed off between multiple agents (sequential delegation, parallel dispatch, nested-call risk). Pick this for auditing how subagents performed, comparing human-vs-agent contribution, or reviewing multi-agent handoffs.

**`analyzing-tool-and-framework-use`** — Inventories external tools actually invoked during a session and auto-detects which developer framework(s) a project uses (GSD, OpenSpec, Speckit, BMAD, GG-SAD, or an unrecognized "other" framework), evaluating role-conformance when a governing-method-plus-execution-companion pairing is detected. Supports a project-level override when auto-detection is ambiguous or absent. Produces tool-use and framework-configuration optimization recommendations. Pick this for a tool-usage inventory or checking whether a project's framework pairing is being used correctly.

## Usability, governance & security

**`analyzing-governance-and-conflicts`** — Analyzes rule/boundary/convention conformance and detects conflicts — agent-vs-agent, rule-vs-rule, spec-vs-code, and session-vs-session — across a session, tracks recurring errors and mistakes, and separately assesses maintainability/change-impact risk (duplication, coupling, stale mirrors, documentation drift, blast radius) exposed by the session's own changes, reported as a second, independent section since structural drift can exist with no rule naming it. Its session-vs-session check is a single unacknowledged-contradiction flag only, not a full structural/semantic comparison between two sessions (see `comparing-sessions` for that), and not a full multi-report cross-check across several analysis-kit reports from the same scope (see `reviewing-analysis-findings` for that). Reuses the shared `component_inventory.py` script for rule evidence. Pick this for rule/spec conformance questions, spotting conflicts between agents, rules, or a spec and the code, or assessing whether a session's changes introduced duplication, coupling, or maintenance risk.

**`analyzing-security-and-privacy`** — Builds a session-scoped threat model -- asset, trust boundary,
threat, evidence, mitigation, residual risk -- covering prompt injection, command injection, credential
exposure, unsafe artifact handling, permission escalation, untrusted code execution, and fail-open safety
behavior. Records only names and locations of sensitive material, never secret values, into the draft.
Maps safety-boundary bypasses to Critical and material defense gaps to Major using the shared severity
vocabulary. Pick this when checking a session for security/privacy risk, building a threat model for what
a session actually touched, or auditing whether a trust boundary was actually respected.

**`analyzing-workflow-usability`** — Analyzes user-facing friction and developer experience in a Claude
Code session -- discoverability, repeated context re-entry, confirmation burden, cognitive load,
correction burden, time-to-first-useful-result, readability, and actionability. Distinguishes necessary
safety gates from avoidable friction by checking whether state or risk actually changed since a prior
answer, and weights human corrections by their consequence rather than counting them equally. Pick this
when checking whether a session's interaction pattern was actually usable, auditing repeated
confirmations or questions for avoidable friction, or judging whether output was readable and actionable.

## Patterns, opportunities & comparisons

**`mining-recurring-patterns`** — Mines a session for recurring action sequences and loops, detects recall/memory-consultation gaps, repeated-question patterns, and retry loops, and aggregates whatever subagent-dispatch token/time usage was actually observed — main-conversation-level token/time totals are explicitly out of scope, since no skill can measure those directly. Pick this for finding repeated command patterns, checking whether the same question was asked more than once, or reviewing where subagent time and tokens went.

**`identifying-feature-opportunities`** — Converts recurring unmet needs and repeated manual work observed
in a Claude Code session (or across persisted analysis-kit reports in scope) into evidence-backed
feature-opportunity candidates -- each scored on reach/expected-value/confidence/effort and gated by an
evidence threshold, so a one-off inconvenience is never promoted to a feature candidate without repeated
evidence or a stated high-consequence impact. Classifies every candidate into exactly one disposition:
candidate, merge-with-existing, insufficient-evidence, or reject. Pick this when spotting a recurring pain
point worth turning into a feature, checking whether an idea already overlaps existing functionality, or
deciding whether a complaint has enough evidence to justify product-level investment.

**`comparing-sessions`** — Compares two Claude Code sessions structurally, using a deterministic diff over two persisted analysis-kit reports, then interprets what changed semantically — component performance trends, suggestion recurrence, tool/framework detection stability, and (optionally) realized impact of an implemented recommendation against the shared recommendation registry. This is a full structural/semantic comparison, not a single contradiction flag (for that narrower check, see `analyzing-governance-and-conflicts`' session-vs-session conflict category), and not multiple different skills' reports from one shared scope (for that, see `reviewing-analysis-findings`). Pick this to see how a project's session-over-session trends have changed.

**`comparing-session-to-specification`** — Checks whether a session's decisions and actions complied with a project's specification, architecture, constitution, or project-brief document, section by section. Pick this to check whether a session followed its own project's spec, architecture doc, or constitution.
