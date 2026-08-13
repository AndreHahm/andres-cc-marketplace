# Scoring Rubric

Twelve dimensions, fixed weights summing to 100%. Every dimension is higher-is-better — none are inverted.

## Generic Formula (Reviewer-Backed Dimensions)

Eight dimensions score from a dispatched reviewer's Critical/Major/Minor (or FAIL/ADVISORY) finding counts, via one shared formula that guarantees severity classes never cross — any Critical always outranks any number of Majors, any Major always outranks any number of Minors:

```
if Critical >= 1:  score = 4 - min(4, 2 * Critical)       # range [0, 2]
elif Major >= 1:   score = 7 - min(3, 1.5 * Major)         # range [4, 5.5]
else:               score = 10 - min(3, 0.5 * Minor)        # range [7, 10]
```

`Rule Compliance` maps `FAIL(REQUIRED) -> Critical`, `ADVISORY(SUGGESTED) -> Minor`; Major is unused (the rulebook has no middle severity tier).

The four remaining dimensions (Simplicity, Testing, Efficiency, Actionability) don't have a Critical/Major/Minor-emitting reviewer behind them — score them directly against the custom bands below and pass the number straight into `dimensions.<name>.score` in `scripts/compute_score.py`'s input (see `output-schema.md`).

## Dimension Table

| # | Dimension | Weight | Signal source(s) | 10 (excellent) | 7 (good) | 4 (needs work) | 0 (broken) |
|---|---|---|---|---|---|---|---|
| 1 | `structure_architecture` | 15% | `skilldir-reviewer` (structural axes), type-matched `*-reviewer`, `plugin-validator` (plugin mode) | No structural findings | Minor only (e.g. generic filename) | 1 Major (e.g. 2-level-deep reference) | Critical (component doesn't resolve / invalid manifest) |
| 2 | `content_quality` | 15% | `skilldir-reviewer` Step 4 (Stale Content) + Step 6 (Broken/Inconsistent Examples) axes only — **not** Step 5, see Dimension 5 | No content findings | Minor only | 1 Major (stale example, wrong example) | Critical (teaches a non-functional pattern) |
| 3 | `rule_compliance` | 12% | `plugin-rulebook-checker` compliance report (via `plugin-auditor`) | All rules PASS | ADVISORY only | — (rulebook has no Major tier) | 1+ REQUIRED FAIL |
| 4 | `completeness` | 12% | `completeness-reviewer` | No open items | Minor only (optional-section stub) | 1 Major (missing required section) | Critical (documented core functionality entirely absent) |
| 5 | `maintainability` | 10% | `consistency-reviewer` (plugin mode), `skilldir-reviewer` Step 5 (Duplicated Content) axis only — component mode | No drift/duplication | Minor duplication noted | 1 Major drift/duplication | 3+ Major (pervasive drift) — treat as Critical-equivalent (score 0) |
| 6 | `robustness` | 10% | `scripts-reviewer` (only if `scripts/` present — otherwise `is_na: true`, score 10) | No findings | Minor only | 1 Major logic bug | Critical (script fails on documented input) |
| 7 | `simplicity` | 5% | R13 tier (`plugin-rulebook`), orphaned-file findings | R13 OK/Weak Warning tier, no orphans | R13 Soft Warning tier, justified | R13 Warning tier unjustified, or 2+ orphaned files | R13 Critical tier, no recorded R13/R18 exception |
| 8 | `testing` | 5% | Static heuristic (no dispatch) | `evals/` + `evals.json` + a completed `benchmark.json` | `evals/`+`evals.json` exist, no run evidence | No `evals/`, but SKILL.md has a concrete Testing & Validation section | Neither — score 0, triggers Gate D |
| 9 | `uniqueness` | 5% | `activation-reviewer` | No overlap findings | Minor/touching-boundary only | 1 Major (domain-overlap/cross-type) | Critical (exact-phrase collision) |
| 10 | `safety_risk_handling` | 5% | `plugin-rulebook` R6 (tool scoping)/R9 (credentials) findings, `security-reviewer` (permission risk, prompt-injection surface, PII/credential-leakage beyond simple regex), `hook-reviewer` (if hooks present), `scripts-reviewer` (credential/injection findings) | No findings, R6-compliant scoping | Minor only | 1 Major (missing confirmation on a risky action) | Critical (destructive action with no guard, or `Bash(*)`) |
| 11 | `efficiency` | 3% | `plugin-rulebook` R13+R18 tiers, Quick Start token check | R13 OK/Weak Warning tier, no R18 Warning-tier-or-worse blocks, concise Quick Start | R13 Soft Warning tier, or 1-2 R18 Warning-tier blocks | R13 Warning tier, or 3+ R18 Warning-tier blocks | R13 Critical tier, or an unremediated R18 Critical-tier block |
| 12 | `actionability` | 3% | Type-matched `*-reviewer` vagueness/imperative-language findings | Concrete Quick Start/procedural steps, no vagueness flagged | 1 Minor vagueness note | Major vagueness (non-imperative, "helps with X" phrasing) | No procedural content at all — pure reference dump |

Weight sum check: 15+15+12+12+10+10+5+5+5+5+3+3 = 100.

## skilldir-reviewer Axis Split: Content Quality vs. Maintainability

`skilldir-reviewer` reports findings across four axes (Step 4 Stale Content, Step 5 Duplicated Content, Step 6 Broken/Inconsistent Examples, Step 7 Rulebook Violations/Broken Links). Its Step 4 and Step 6 axes feed `content_quality`; its Step 5 axis feeds `maintainability` instead. Do not assign a Step 5 (Duplicated Content) finding to `content_quality`, and do not assign a Step 4 or Step 6 finding to `maintainability` — each finding has exactly one home dimension. (Its Step 7 axis feeds `rule_compliance` via the same rulebook violations it flags, not either of these two.)

This split was ambiguous in an earlier version of this rubric — both dimensions listed "skilldir-reviewer" as a shared, unqualified source, which required an ad-hoc judgment call during this skill's own first live test run to avoid double-counting the same finding (or scoring it under the wrong dimension) when a `skilldir-reviewer` report mixed stale-content and duplicated-content findings together. Route by the finding's stated axis, not by which dimension "feels closer."

## safety_risk_handling: plugin-rulebook vs. security-reviewer

Both sources feed the same dimension but cover different ground — `plugin-rulebook`'s R6/R9 checks are structural pattern-matching (an unscoped `Bash(*)`, a bare `Bash`, a hardcoded-looking secret string); `security-reviewer` goes deeper into the same risk category (a technically-scoped-but-still-over-broad grant like `Bash(python */scripts/<name>.py:*)` matching a same-named script in an unrelated analyzed repo, a missing data-only boundary around untrusted content, a credential-shaped value that would leak into a persisted report). When both sources flag what is genuinely the *same* underlying gap from two angles, count it once — file it as a `security-reviewer` finding if it names the specific mechanism (a Major from `security-reviewer` naming an exact over-broad grant outranks a structural R6 PASS that didn't catch it), not as two separate findings inflating the count. This dimension was previously the second time this exact gap-class surfaced in this plugin's own history without a hard gate to catch it (see `gates-and-rollup.md`) — `security-reviewer` was added as a named source specifically because grading passes before this fix had to invent an undocumented ad-hoc mapping to count its findings at all.

## Dimension-Level Cap: Contradictory Instructions

If the target contains self-contradicting guidance (e.g. one section states a rule, another section violates it — the "ABSOLUTE DENY vs ABSOLUTE DECLINE" class of bug), set `dimensions.content_quality.contradiction_found: true` in the script input. This caps Content Quality at 4 *before* the weighted sum, regardless of what the generic formula would otherwise produce. It is not a separate hard gate — Content Quality's 15% weight already makes this cap meaningfully felt in the total.

## N/A Handling

If a dimension's signal source genuinely doesn't apply (e.g. `robustness` when no `scripts/` exists), score it **10** with `is_na: true`. Never exclude a dimension or renormalize weights — the 12 fixed weights stay stable in every output.

## Type-Matched Reviewer Table

**Since M3: informational here, not the dispatch source.** `plugin-auditor` (see its own
`references/dispatch-table.md`) is what actually decides and runs this dispatch now — this table
stays here because Step 4's dimension mapping still needs to know which reviewer backs
`structure_architecture`/`content_quality`/`actionability` for a given target type. If the mapping
ever changes, update `plugin-auditor`'s copy first and mirror it here, not the other way around.

| Target type | Reviewer for Structure/Content/Actionability |
|---|---|
| Skill | `skill-reviewer` (SKILL.md) + `skilldir-reviewer` (everything else) |
| Agent | `subagent-reviewer` |
| Command | `command-reviewer` |
| Hook | `hook-reviewer` |
| Rule | `rule-reviewer` |

Dispatch only the reviewer(s) matching the target's actual type — never all five.
