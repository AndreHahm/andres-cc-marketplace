<!--
SCORE_CARD TEMPLATE — usage notes (delete this comment block when instantiating)

Purpose: a repeatable, comparable evaluation of a plugin or a single plugin
component (skill, sub-agent, command, rule/reference doc, hook, script).
One scorecard = one subject. Do not score multiple components in one file.

Naming convention for instantiated files:
  docs/scorecards/<component-type>-<slug>-SCORE_CARD.md
  e.g. docs/scorecards/plugin-wiki-cortex-SCORE_CARD.md
       docs/scorecards/command-research-SCORE_CARD.md
       docs/scorecards/skill-wiki-manager-SCORE_CARD.md

Scoring scale (all dimensions): 0-5 integer.
  0 = Absent / not applicable but expected
  1 = Present but broken or seriously deficient
  2 = Below bar — works sometimes, notable gaps
  3 = Meets bar — works as documented, no major gaps
  4 = Strong — well above bar, thoughtful edge-case handling
  5 = Exemplary — reference-quality, nothing meaningful to improve

Leave a dimension's score blank (`—`) and explain in Notes if it does not
apply to this component type (e.g., "Test Coverage" may not apply to a raw
markdown rule file with no executable behavior).

Cross-reference `docs/SWOT.md`, `docs/ROADMAP.md`, and `docs/TODOs.md` where
relevant instead of re-deriving findings from scratch.
-->

---
title: "SCORE_CARD: <Component Name>"
component_type: plugin|skill|sub-agent|command|rule|hook|script|reference-doc
component_path: "<relative path, e.g. plugins/wiki-cortex/commands/research.md>"
plugin: "<owning plugin, e.g. wiki-cortex>"
version_or_commit: "<version tag or git SHA evaluated>"
evaluated_by: "<name or agent>"
evaluated_date: YYYY-MM-DD
related_swot: "docs/SWOT.md#<anchor>"
related_roadmap: "docs/ROADMAP.md#<anchor>"
related_todos: ["<TODO id, e.g. P1-2>"]
overall_score: 0.0
overall_grade: A|B|C|D|F
status: draft|reviewed|final
---

# SCORE_CARD: <Component Name>

> One-line summary of what this component is and does.

## 1. Identity

| Field | Value |
|---|---|
| **Type** | plugin \| skill \| sub-agent \| command \| rule \| hook \| script \| reference-doc |
| **Path** | `<path>` |
| **Owning Plugin** | `<plugin name>` |
| **Version / Commit** | `<value>` |
| **Evaluated By** | `<name/agent>` |
| **Evaluated Date** | `YYYY-MM-DD` |
| **Lines / Size** | `<line count or byte size, if relevant>` |
| **Dependencies** | `<other components, tools, MCP servers, external CLIs this relies on>` |
| **Depended On By** | `<other components that call/reference this one>` |

## 2. Scope Statement

What this component is *supposed* to do, in the evaluator's own words (not
copy-pasted from its own docs — this catches doc/behavior drift).

- **Intended purpose**: <...>
- **Explicit non-goals** (per its own docs, if stated): <...>
- **Trigger/invocation** (how it's activated — slash command, natural language, hook event, sub-agent delegation, etc.): <...>

## 3. Responsibilities, Boundaries & Constraints

### Responsibilities

What this component owns and is accountable for. Be specific — "manages the
wiki" is too broad; "resolves HUB path and validates topic wiki existence
before any subcommand runs" is right-sized.

- **<Responsibility 1>**: <...>
- **<Responsibility 2>**: <...>

### Boundaries

What this component explicitly does **not** do, and where that work is
handed off instead. A component with unclear boundaries is a scope-creep and
router-ambiguity risk (see `docs/SWOT.md` §Cross-Command Patterns).

| Adjacent component | Boundary line | Hand-off direction |
|---|---|---|
| `<sibling component>` | <where this component stops and the sibling starts> | delegates to \| receives from \| peer (no overlap) |

- **Out-of-scope inputs/requests**: <what a user/caller might reasonably ask this component to do, that it should refuse or redirect>

### Constraints

Technical, permission, and environmental limits this component must operate
within.

| Constraint type | Value | Notes |
|---|---|---|
| **Tool/permission scope** | `<e.g. allowed-tools list, read-only vs. read-write>` | least-privilege check — flag anything broader than actually used |
| **Invocation context** | `<e.g. must run inside a resolved topic wiki, requires HUB, project-local only>` | |
| **External dependencies** | `<CLIs, MCP servers, APIs, network access required>` | note any that are optional vs. hard requirements |
| **Data mutation limits** | `<e.g. never deletes raw/, dry-run required for bulk writes>` | |
| **Concurrency/state assumptions** | `<e.g. assumes single-writer, no locking>` | |
| **Performance/token budget** | `<e.g. governed by tests/budgets/token-budgets.json>` | |

Unstated or undocumented constraints discovered during evaluation should be
recorded here even if the component's own docs omit them — this is often
where real risk hides.

## 4. Scoring Dimensions

| Dimension | Score (0-5) | Weight | Weighted | Notes |
|---|---|---|---|---|
| **Correctness & Reliability** — does it do what it claims, consistently? | | 20% | | |
| **Documentation Quality** — is the spec/description clear, complete, and accurate vs. actual behavior? | | 10% | | |
| **Test Coverage** — structural/behavioral/benchmark coverage proportional to risk | | 15% | | |
| **Security & Privacy** — handles secrets/PII/untrusted input safely; least-privilege tool access | | 15% | | |
| **Performance & Efficiency** — token/context cost, latency, redundant work | | 10% | | |
| **Maintainability** — readability, duplication, coupling to other components | | 10% | | |
| **Scope Discipline** — stays within its stated boundary; doesn't overlap/compete with sibling components | | 10% | | |
| **Composability & Reusability** — plays well with other components (shared references, consistent conventions) | | 5% | | |
| **User Experience** — clarity of inputs/flags/output, error messages, recoverability | | 5% | | |
| **Total** | | 100% | **<sum>** | |

Weighting guidance: adjust weights per component type before scoring (e.g.,
a `rule`/reference-doc component may set Test Coverage weight to 0% and
redistribute; a `hook`/`script` may raise Security weight). Record any
weight changes in §8 Methodology Notes.

**Overall Score**: `<weighted sum> / 5.0`
**Overall Grade**: A (4.5-5.0) / B (3.5-4.49) / C (2.5-3.49) / D (1.5-2.49) / F (<1.5)

## 5. Strengths

- **<Strength 1>**: <why it matters, cite `docs/SWOT.md` if already documented>
- **<Strength 2>**: <...>

## 6. Weaknesses & Risks

- **<Weakness 1>**: <impact, severity, cite `docs/SWOT.md` if already documented>
- **<Weakness 2>**: <...>

## 7. Recommended Actions

| Priority | Action | Type | Linked TODO |
|---|---|---|---|
| P0/P1/P2/P3 | <action> | tech-debt\|security\|testing\|feature\|process\|docs | `<TODO id or "new">` |

If an action isn't already tracked in `docs/TODOs.md`, add it there and
reference the new ID here.

## 8. Methodology Notes

- **Weight adjustments made**: <none, or list with rationale>
- **Dimensions marked N/A**: <list with rationale>
- **Evidence sources used**: <files read, tests run, benchmarks consulted>
- **Confidence in this scorecard**: high|medium|low — <why>

## 9. Revision History

| Date | Evaluator | Overall Score | Change Summary |
|---|---|---|---|
| YYYY-MM-DD | <name> | <score> | Initial scorecard |
