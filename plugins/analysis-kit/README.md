# Analysis Kit

Session analysis toolkit for Claude Code: component retrospectives, tool/framework auditing, actor behavior analysis, governance and conflict detection, session/specification comparison, recurring-pattern mining, cross-report findings review, classified improvement recommendations, and third-party review-learnings mining/management — grounded in a session, date range, or a set of merged PRs, with reports persisted for later reference, a guided front door (`starting-an-analysis`) that picks the right analysis type without needing to already know the other skills' names, and a multi-run orchestrator (`running-a-full-retrospective`) that runs several of those analyses at once, consolidates their findings, and hands off to a guided fix pass.

## Plugin Target

- Turn a completed development session into a concrete, prioritized improvement backlog
- Catch systemic issues that span more than one component, not just isolated bugs
- Re-verify prior artifacts' own "still open" claims against current repo state instead of trusting them at face value
- Identify which external tools and developer frameworks a session actually used, and whether a framework's execution companion stayed within its subordinate role
- Assess agent behavior, human contribution, and cross-agent handoffs
- Detect rule/boundary conformance issues and conflicts across agents, rules, specs, and sessions
- Compare sessions to each other, or to a specification/architecture/constitution document
- Mine recurring action sequences, loops, and recall gaps, and turn any finding into a concrete action plan
- Mine merged PRs for recurring third-party review-learning patterns, propose them into a shared learnings document, and delegate any resulting GitHub issue to `git-kit`

## Overview

`analysis-kit` provides 13 skills over a shared deterministic `scripts/` core (component/rule inventory, framework fingerprinting, structural diffing, sequence mining, usage aggregation, session parsing, PR review-history fetching, secret redaction, report persistence — see the Skills table below for what each skill does). Reports from every report-producing skill are persisted under `.claude/output/<skill-name>/`, one file per run, so later runs can reference a specific prior report (`starting-an-analysis` is the one skill that persists nothing of its own — it only dispatches). Before any report is written, every skill runs its scratch draft through `scripts/persist_report.py` — a shared wrapper that redacts common secret-shaped patterns (Authorization/Bearer headers, `.env`-shaped lines, known cloud key prefixes) via `scripts/redact_secrets.py`, verifies the result and the written file are both LF-only, writes the final file, and prints the standard `📄 ... written:` confirmation line — refusing to write and exiting non-zero instead if the redacted text (or, after writing, the file itself) still contains CRLF sequences, or if the scratch draft can't be read at all. This centralizes a 6-step ritual every report-producing skill previously re-described independently in prose, behind one call site instead of twelve.

This plugin has no hard dependency required just to install and run its core analysis skills, but two skills reach outside it, and neither stays entirely within `analysis-kit` once its own fix/file step actually runs. `running-a-full-retrospective`'s Phase 5 fix loop needs both companion plugins, not just one: `plugin-devkit`'s `plugin-rulebook` compliance check runs unconditionally on *either* of Phase 5's two paths (its own Step 4), and the direct-fix path additionally runs `git-kit`'s full `starting-work` → `commit` → `create-pr` → `merge-pr` → `finishing-work` chain, while the hand-off path instead dispatches `plugin-devkit`'s `plugin-lifecycle-downstream` (at its External Entry point). Declining Phase 5 entirely (stopping at the consolidated report) is the only way to keep a `running-a-full-retrospective` run inside `analysis-kit` alone. `managing-review-learnings`' Phase 4 dispatches `git-kit`'s `github-issue-lifecycle` to actually file an approved candidate as a GitHub issue — this one has no graceful "skip and continue" path if `git-kit` isn't installed (Phase 4 has nothing to fall back to and states that plainly rather than failing silently), so treat `git-kit` as an effectively required companion plugin if that specific skill's issue-filing step will actually be used.

**Real session data, where it's available.** Five skills with a date-range scope (`analyzing-plugin-components`, `analyzing-tool-and-framework-use`, `analyzing-actor-behavior`, `analyzing-governance-and-conflicts`, `mining-recurring-patterns`) first try `scripts/session_parser.py` to parse Claude Code's own local session JSONL (format confirmed against a real file, not guessed), then `scripts/codex_session_parser.py` for a named Codex CLI session file (format unconfirmed, so it's parsed defensively — detect, attempt, report unparseable rather than guess), and only fall back to asking the user to paste transcript excerpts when neither produces usable data. Deliberately not built: a full canonical event schema or byte-offset/event-ID provenance — both scripts report light provenance only (source file, session id, timestamp range). `mining-recurring-patterns`' token/time reporting reflects this: it ranks top-10 tokens/duration by skill invocation when session data is available, and always still ranks top-10 by subagent dispatch (the one source of real usage data every skill can observe regardless of session-file availability) — it never claims whole-session totals, since no skill can measure those directly. `mining-review-learnings` is a sixth, differently-shaped consumer of both parsers: rather than a bare date-range scope, it runs `session_parser.py` with a padded `--since`/`--until` window derived from each mined PR's own merge window, and does its own `Glob` discovery of Codex session files under `~/.codex/sessions/<YYYY>/<MM>/<DD>/` before ever calling `codex_session_parser.py` — that script itself has no discovery of its own.

**Shared severity vocabulary.** `references/severity-vocabulary.md` (plugin root, not under any single skill) defines a 4-tier scale (Critical/Major/Minor/Informational) that the skills with a severity-rated vocabulary — P1/P2/P3, Violated/Compliant/Ambiguous, and so on — map onto, so a reader (or `reviewing-analysis-findings`) can compare two differently-worded severity claims on one consistent basis. It doesn't replace any skill's own vocabulary; each skill keeps its native terms. Not every skill rates findings by severity (see the reference file itself for which ones don't and why).

**Shared report-discovery convention.** `references/report-discovery-convention.md` (plugin root) is the canonical definition of the `<scope-slug>` filename convention and the report-discovery glob every skill's own "latest report" / "next step" logic restates inline — read it before changing either in any individual skill, and sweep every site it lists in the same pass.

**Shared date-range scope convention.** `references/date-range-scope-convention.md` (plugin root) is the canonical Phase 1 scope-resolution procedure the 5 date-range skills (`analyzing-plugin-components`, `analyzing-tool-and-framework-use`, `analyzing-actor-behavior`, `analyzing-governance-and-conflicts`, `mining-recurring-patterns`) each restate by reference in their own Phase 1 — read it before changing the procedure, and sweep every site it lists in the same pass.

**Activation-collision fix convention.** Where two skills' domains genuinely overlap (e.g. a bare "run a retrospective" request could plausibly match either `analyzing-plugin-components` or `starting-an-analysis`; "which subagents ran" could match either `analyzing-tool-and-framework-use`'s tool inventory or `analyzing-actor-behavior`'s dispatch-quality assessment), this plugin resolves the ambiguity per the repo-wide convention in `.claude/rules/resolve-activation-overlap-bidirectionally.md`: an explicit, reciprocal textual exclusion — each skill's own "When to Use"/"When NOT to Use" section names the specific sibling skill and states the exact distinguishing criterion (not just "see the other skill" — the actual axis that separates them, e.g. "counts *that* a subagent was invoked" vs. "assesses *how well* it performed"), always bidirectional. This same pattern closed the original `analyzing-plugin-components`/`starting-an-analysis` collision and the `analyzing-tool-and-framework-use`/`analyzing-actor-behavior` and `analyzing-governance-and-conflicts`/`mining-recurring-patterns` overlaps found in later audits.

**Two more disclosed design choices, recorded here rather than left implicit:** `analyzing-governance-and-conflicts` and `comparing-session-to-specification` both `Glob` a generic `specs/` directory as one of several spec-document search locations — this is unrelated to, and shouldn't be confused with, the low-confidence Spec Kit marker of the same name (`specs/`) in `analyzing-tool-and-framework-use`'s `assets/framework-signatures.json`; the two uses of the string are coincidental, not a shared assumption. Separately, ten skills depend on `.claude/output/` beyond a bare existence check, which is gitignored by convention — this persist-then-read pipeline is an accepted, intentional design choice, not an oversight. Nine of them read a prior report's actual content (`analyzing-plugin-components`, `analyzing-governance-and-conflicts`, `comparing-sessions`, `comparing-session-to-specification`, `generating-analysis-recommendations`, `mining-recurring-patterns`, `reviewing-analysis-findings`, `running-a-full-retrospective`, `managing-review-learnings` — the last reads a `mining-review-learnings` report); the tenth, `starting-an-analysis`, doesn't read content itself but dispatches a downstream skill against a report path it discovered via `Glob` — a real dependency on the same gitignored artifacts, just one step removed. `mining-review-learnings` itself doesn't depend on `.claude/output/` this way — it only writes its own report there, the same as every skill trivially does; it never reads a prior report as input. The remaining two date-range skills, `analyzing-actor-behavior` and `analyzing-tool-and-framework-use`, only `Glob` for an existence check in their own Next-step block — no content read and no downstream dispatch keyed off what's found — so they're not counted among the nine, though the same graceful-degradation rationale below covers them too. It's a deliberate exception to the general rule against referencing a gitignored path as a live dependency, justified on two grounds specific to this case: every consuming site degrades gracefully when the artifact is absent (offers to generate a baseline, skips, or falls back to pasted findings, rather than failing), and the artifacts in question are self-produced by this same plugin's own skills, not an external dependency that could vanish for reasons outside the plugin's control.

## Prerequisites

Every skill that calls a shared script shells out to `python` (must resolve to Python 3.9+ on PATH — several scripts use PEP 585 builtin generics that fail on 3.8 and earlier). `scripts/pr_review_fetcher.py`'s own test suite (`tests/test_pr_review_fetcher.py`, 12 tests) additionally requires `pytest` — not needed to run any skill, only to develop against this plugin's own scripts.

## Installation

```bash
/plugin install analysis-kit@andres-cc-marketplace
```

Or for local development:

```bash
cc --plugin-dir /path/to/analysis-kit
```

## Quick Start

These are skills, not slash commands — invoke them by name in natural language, e.g. "run
`starting-an-analysis`" or "run `analyzing-plugin-components` since 2026-07-10":

```
# Not sure which analysis type fits? Start here — it asks, scopes, confirms, runs, then offers the next step.
> run starting-an-analysis

# Want several analyses run and consolidated into one prioritized list?
> run running-a-full-retrospective

# Already know the skill you want? Invoke it directly:

# Post-session component retrospective, current conversation
> run analyzing-plugin-components

# Post-session component retrospective, since a given date
> run analyzing-plugin-components since 2026-07-10

# Tool and framework use for the current conversation
> run analyzing-tool-and-framework-use

# Expand a prior finding into a WHAT/WHY/HOW action plan
> run generating-analysis-recommendations on .claude/output/analyzing-plugin-components/this-conversation-2026-08-01T12-00-00Z.md
```

1. Not sure which single analysis type fits, or want the analyze → expand-findings flow for one report walked through step by step? Run `starting-an-analysis` — it picks the type, asks for scope, confirms before running anything, then offers the next step once a report exists.
2. Want several analyses run over the same scope and consolidated into one prioritized action list, then optionally handed off to a guided fix pass? Run `running-a-full-retrospective` instead.
3. Already know the skill you want? Invoke it directly and choose scope yourself — this conversation, a start date, or today (most skills), a report/document path (the comparison and recommendation skills), or a PR number list/merge-date range/"since last cited" (`mining-review-learnings`) and a `mining-review-learnings` report path or named finding (`managing-review-learnings`).
4. Each skill runs its own deterministic first step (a shared script, or a component inventory) before any semantic interpretation.
5. Review findings in priority order.
6. Act on the recommendations, then check the persisted report path — or hand a specific finding to `generating-analysis-recommendations` for a concrete plan.

## Skills

| Skill | Use when |
|---|---|
| `starting-an-analysis` | Not already knowing which of the 7 report-producing analysis skills below fits — a guided front door that picks the type, scopes it, confirms before running, and offers the next step afterward |
| `running-a-full-retrospective` | Wanting several of the 5 date-range analysis skills below (not the 2 comparison skills, which take a comparison target rather than a bare scope) run over the same scope and consolidated into one deduplicated, prioritized action list, then optionally handed off to `plugin-devkit`'s `plugin-lifecycle-downstream` for a guided fix pass — not one analysis type at a time |
| `analyzing-plugin-components` | Running a post-session retrospective, auditing skill/agent/rule performance, or building a prioritized improvement backlog from a session or date range |
| `analyzing-tool-and-framework-use` | Auditing which external tools or developer frameworks a session actually used, or checking whether a framework's execution companion stayed within its subordinate role |
| `analyzing-actor-behavior` | Assessing agent behavior, human-vs-agent contribution, or cross-agent handoff/flow patterns |
| `analyzing-governance-and-conflicts` | Checking rule/boundary conformance, or finding conflicts between agents, rules, specs, or sessions |
| `comparing-sessions` | Comparing this session to a prior one, or checking whether a prior session's suggestions were acted on |
| `comparing-session-to-specification` | Checking whether a session's decisions complied with a specification, architecture, or constitution document |
| `mining-recurring-patterns` | Finding repeated action sequences, checking for repeated questions, or reviewing skill/subagent token/time hotspots |
| `generating-analysis-recommendations` | Turning any finding from another analysis-kit skill into a classified WHAT/WHY/HOW action plan |
| `reviewing-analysis-findings` | Cross-checking 2+ analysis-kit reports from the same scope for duplicate findings, contradictions, or a severity claim one report's evidence undercuts |
| `mining-review-learnings` | Mining a set of merged PRs (an explicit list, a merge-date range, or everything since the last PR cited in `THIRD_PARTY_REVIEW_LEARNINGS.md`) for new, generalizable review-finding patterns, cross-checking GitHub review history against session transcripts |
| `managing-review-learnings` | Turning a `mining-review-learnings` report into a proposed diff to `THIRD_PARTY_REVIEW_LEARNINGS.md`, checking `.claude/rules/` coverage, and — only for candidates that survive both — dispatching `git-kit`'s `github-issue-lifecycle` to file one |

## Configuration

`analysis-kit` ships a git-tracked default at `analysis-kit.settings.json` (plugin root) with a `framework_override` field, used by `analyzing-tool-and-framework-use`'s auto-detection. Set an optional `.claude/analysis-kit.local.json` (gitignored, per-project) with the same field to override auto-detection for that project — the local override always wins over both the plugin default and auto-detection.

## License

Apache-2.0 — see [`LICENSE`](./LICENSE).

## Attribution

`analysis-kit` began as a standalone port of the `analyzing-sessions` skill originally built inside this marketplace's `plugin-devkit` plugin, renamed to `analyzing-plugin-components` and decoupled from that plugin's other components so it carries no cross-plugin dependency of its own — see "Overview" above for the one later, optional exception (`running-a-full-retrospective`'s Phase 5 hand-off).
