# Analysis Kit

Session analysis toolkit for Claude Code: component retrospectives, tool/framework auditing, actor behavior analysis, governance and conflict detection, session/specification comparison, recurring-pattern mining, cross-report findings review, and classified improvement recommendations — all grounded in a session or date range, with reports persisted for later reference.

## Plugin Target

- Turn a completed development session into a concrete, prioritized improvement backlog
- Catch systemic issues that span more than one component, not just isolated bugs
- Re-verify prior artifacts' own "still open" claims against current repo state instead of trusting them at face value
- Identify which external tools and developer frameworks a session actually used, and whether a framework's execution companion stayed within its subordinate role
- Assess agent behavior, human contribution, and cross-agent handoffs
- Detect rule/boundary conformance issues and conflicts across agents, rules, specs, and sessions
- Compare sessions to each other, or to a specification/architecture/constitution document
- Mine recurring action sequences, loops, and recall gaps, and turn any finding into a concrete action plan

## Overview

`analysis-kit` provides 9 skills over a shared deterministic `scripts/` core (component/rule inventory, framework fingerprinting, structural diffing, sequence mining, usage aggregation, session parsing, secret redaction — see the Skills table below for what each skill does). Reports from every skill are persisted under `.claude/output/<skill-name>/`, one file per run, so later runs can reference a specific prior report. Before any report is written, every skill runs it through `scripts/redact_secrets.py` — a shared pass that strips common secret-shaped patterns (Authorization/Bearer headers, `.env`-shaped lines, known cloud key prefixes) without ever blocking the write.

This plugin is standalone — it has no dependency on any other plugin.

**Real session data, where it's available.** Five skills with a date-range scope (`analyzing-plugin-components`, `analyzing-tool-and-framework-use`, `analyzing-actor-behavior`, `analyzing-governance-and-conflicts`, `mining-recurring-patterns`) first try `scripts/session_parser.py` to parse Claude Code's own local session JSONL (format confirmed against a real file, not guessed), then `scripts/codex_session_parser.py` for a named Codex CLI session file (format unconfirmed, so it's parsed defensively — detect, attempt, report unparseable rather than guess), and only fall back to asking the user to paste transcript excerpts when neither produces usable data. Deliberately not built: a full canonical event schema or byte-offset/event-ID provenance — both scripts report light provenance only (source file, session id, timestamp range). `mining-recurring-patterns`' token/time reporting reflects this: it ranks top-10 tokens/duration by skill invocation when session data is available, and always still ranks top-10 by subagent dispatch (the one source of real usage data every skill can observe regardless of session-file availability) — it never claims whole-session totals, since no skill can measure those directly.

**Shared severity vocabulary.** `references/severity-vocabulary.md` (plugin root, not under any single skill) defines a 4-tier scale (Critical/Major/Minor/Informational) that the skills with a severity-rated vocabulary — P1/P2/P3, Violated/Compliant/Ambiguous, and so on — map onto, so a reader (or `reviewing-analysis-findings`) can compare two differently-worded severity claims on one consistent basis. It doesn't replace any skill's own vocabulary; each skill keeps its native terms. Not every skill rates findings by severity (see the reference file itself for which ones don't and why).

**Two more disclosed design choices, recorded here rather than left implicit:** `analyzing-governance-and-conflicts` and `comparing-session-to-specification` both `Glob` a generic `specs/` directory as one of several spec-document search locations — this is unrelated to, and shouldn't be confused with, the low-confidence Spec Kit marker of the same name (`specs/`) in `analyzing-tool-and-framework-use`'s `assets/framework-signatures.json`; the two uses of the string are coincidental, not a shared assumption. Separately, six skills (`analyzing-plugin-components`, `comparing-sessions`, `comparing-session-to-specification`, `generating-analysis-recommendations`, `mining-recurring-patterns`, `reviewing-analysis-findings`) depend on reading prior reports from `.claude/output/`, which is gitignored by convention — this persist-then-read pipeline is an accepted, intentional design choice, not an oversight. It's a deliberate exception to the general rule against referencing a gitignored path as a live dependency, justified on two grounds specific to this case: every consuming site degrades gracefully when the artifact is absent (offers to generate a baseline, skips, or falls back to pasted findings, rather than failing), and the artifacts in question are self-produced by this same plugin's own skills, not an external dependency that could vanish for reasons outside the plugin's control.

## Prerequisites

Every skill that calls a shared script shells out to `python` (must resolve to Python 3.9+ on PATH — several scripts use PEP 585 builtin generics that fail on 3.8 and earlier).

## Installation

```bash
/plugin install analysis-kit@andres-cc-marketplace
```

Or for local development:

```bash
cc --plugin-dir /path/to/analysis-kit
```

## Quick Start

```bash
# Post-session component retrospective, current conversation
> /analyzing-plugin-components

# Post-session component retrospective, since a given date
> /analyzing-plugin-components 2026-07-10

# Tool and framework use for the current conversation
> /analyzing-tool-and-framework-use

# Expand a prior finding into a WHAT/WHY/HOW action plan
> /generating-analysis-recommendations .claude/output/analyzing-plugin-components/this-conversation-2026-08-01T12-00-00Z.md
```

1. Choose scope — this conversation, a start date, or today (most skills), or a report/document path (the comparison and recommendation skills).
2. Each skill runs its own deterministic first step (a shared script, or a component inventory) before any semantic interpretation.
3. Review findings in priority order.
4. Act on the recommendations, then check the persisted report path — or hand a specific finding to `generating-analysis-recommendations` for a concrete plan.

## Skills

| Skill | Use when |
|---|---|
| `analyzing-plugin-components` | Running a post-session retrospective, auditing skill/agent/rule performance, or building a prioritized improvement backlog from a session or date range |
| `analyzing-tool-and-framework-use` | Auditing which external tools or developer frameworks a session actually used, or checking whether a framework's execution companion stayed within its subordinate role |
| `analyzing-actor-behavior` | Assessing agent behavior, human-vs-agent contribution, or cross-agent handoff/flow patterns |
| `analyzing-governance-and-conflicts` | Checking rule/boundary conformance, or finding conflicts between agents, rules, specs, or sessions |
| `comparing-sessions` | Comparing this session to a prior one, or checking whether a prior session's suggestions were acted on |
| `comparing-session-to-specification` | Checking whether a session's decisions complied with a specification, architecture, or constitution document |
| `mining-recurring-patterns` | Finding repeated action sequences, checking for repeated questions, or reviewing skill/subagent token/time hotspots |
| `generating-analysis-recommendations` | Turning any finding from another analysis-kit skill into a classified WHAT/WHY/HOW action plan |
| `reviewing-analysis-findings` | Cross-checking 2+ analysis-kit reports from the same scope for duplicate findings, contradictions, or a severity claim one report's evidence undercuts |

## Configuration

`analysis-kit` ships a git-tracked default at `analysis-kit.settings.json` (plugin root) with a `framework_override` field, used by `analyzing-tool-and-framework-use`'s auto-detection. Set an optional `.claude/analysis-kit.local.json` (gitignored, per-project) with the same field to override auto-detection for that project — the local override always wins over both the plugin default and auto-detection.

## License

Apache-2.0 — see [`LICENSE`](./LICENSE).

## Attribution

`analysis-kit` began as a standalone port of the `analyzing-sessions` skill originally built inside this marketplace's `plugin-devkit` plugin, renamed to `analyzing-plugin-components` and decoupled from that plugin's other components so it has no cross-plugin dependency.
