# Dispatch Table

Ported from `plugin-grader/references/rubric.md`'s Type-Matched Reviewer Table and Step 3
dispatch logic — same reviewer set, with `Skill(plugin-rulebook)` replaced by the
`plugin-rulebook-checker` agent (Structured output mode, per this repo's Settled Decision 2
for the `plugin-lifecycle-downstream` redesign) and `dependency-reviewer` added, since
`plugin-grader` never dispatches it today.

## Type-Matched Reviewer Table

| Target type | Reviewer for Structure/Content/Actionability |
|---|---|
| Skill | `skill-reviewer` (SKILL.md) + `skilldir-reviewer` (everything else) |
| Agent | `subagent-reviewer` |
| Command | `command-reviewer` |
| Hook | `hook-reviewer` |
| Rule | `rule-reviewer` |

Dispatch only the reviewer(s) matching the target's actual type — never all five.

## Component Mode

For a single component, or the scope manifest's declared component set when Phase 5 covers
more than one (a `changed`/`named` scope with several components), dispatch in parallel:

- `skilldir-reviewer` (skills with non-`SKILL.md` files only)
- The type-matched `*-reviewer` from the table above
- `completeness-reviewer`
- `activation-reviewer`
- `security-reviewer`
- `dependency-reviewer` — Full review, scoped to exactly the declared component set (its own
  Step 1 already supports "the caller names specific components, resolve each via `Glob` and
  use exactly that set"); use its Delta mode instead when the scope manifest names exactly
  one new `Skill()`/`Agent()` edge just added, per its own Invocation Modes
- `scripts-reviewer` — only if `scripts/` exists for the target
- `hook-reviewer` — only if the target has hooks (a hook component, or a skill/agent
  declaring `hooks:` frontmatter)
- `plugin-rulebook-checker` agent, Structured output mode — replaces `Skill(plugin-rulebook)`

## Plugin Mode

Dispatch the component-mode set above per component (batched across all components), **plus**
run once across the whole set (not once per component):

- `activation-reviewer` in whole-plugin mode → cross-component overlap findings
- `consistency-reviewer` across all components → drift/duplication findings
- `dependency-reviewer` in whole-plugin mode (Full review, no named subset) → the graph-wide
  cycle/bidirectional/broken-target findings a per-component scoped call can't see
- `plugin-validator` in its default Full-review mode → structural/manifest findings

## Reuse Pre-Supplied Findings

Don't re-dispatch a check that already ran. If the caller (typically
`plugin-lifecycle-downstream`, reusing its own Phase 3 Validate results) supplies
`plugin-rulebook-checker` and/or `plugin-validator` findings for some or all of the
component(s) in scope, use those directly instead of dispatching either agent again for the
same component. This applies per-component: pre-supplied findings that only cover some
components (e.g. from a Scoped Phase 3 run) don't excuse skipping the rest — dispatch fresh
for whichever components weren't already covered. A full-mode whole-plugin `plugin-validator`
report isn't pre-split by component the way a `plugin-rulebook-checker` batch report is, but
every finding in it already cites the specific file(s)/component(s) it applies to — extract
per-component findings from that one report rather than treating "not pre-split" as a reason
to re-dispatch.

## Not This Skill's Job

The Testing static heuristic (`Glob` for `evals/`/`evals.json`/`benchmark.json`, `Grep`
SKILL.md for a Testing & Validation section) stays with `plugin-grader` in both its
standalone and evidence-only modes — `plugin-grader`'s own Step 3 already treats it as a
direct check, not a dispatch ("Also run the Testing static heuristic directly (no
dispatch)"), so it was never part of the reviewer-dispatch step this skill extracts.
Scoring, gates, and SWOT/next-steps derivation are `plugin-grader`'s job — this skill
produces normalized evidence only.
