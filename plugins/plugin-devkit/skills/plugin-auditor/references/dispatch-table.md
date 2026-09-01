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

For a single component, dispatch in parallel:

- `skilldir-reviewer` (skills with non-`SKILL.md` files only)
- The type-matched `*-reviewer` from the table above
- `completeness-reviewer`
- `activation-reviewer`
- `security-reviewer`
- `dependency-reviewer` — Full review, scoped to exactly this one component; use its Delta
  mode instead when the caller names exactly one new `Skill()`/`Agent()` edge just added, per
  its own Invocation Modes
- `authority-reviewer` — Full review, scoped to exactly this one component; use its Delta
  mode instead when the caller names exactly one specific precedence/authority claim just
  added or changed, per its own Invocation Modes
- `scripts-reviewer` — only if `scripts/` exists for the target
- `hook-reviewer` — only if the target has hooks (a hook component, or a skill/agent
  declaring `hooks:` frontmatter)
- `plugin-rulebook-checker` agent, Structured output mode — replaces `Skill(plugin-rulebook)`

## Plugin Mode

Dispatch the component-mode set above per component (batched across all components) —
**excluding `dependency-reviewer` and `authority-reviewer`**, whose per-component Full
review can't detect anything their own Steps 4/5 contradiction/cycle checks are actually
for (a graph built from one component's own edges only has nothing else to compare
against), and whose only other real check (broken-target resolution) is already a strict
subset of what the whole-plugin dispatch below covers — dispatching them per component
here as well would invoke each one N+1 times for an N-component plugin with no added
signal, **plus** run once across the whole set (not once per component):

- `activation-reviewer` in whole-plugin mode → cross-component overlap findings
- `consistency-reviewer` across all components → drift/duplication findings
- `dependency-reviewer` in whole-plugin mode (Full review, no named subset) → the graph-wide
  cycle/bidirectional/broken-target findings a per-component scoped call can't see
- `authority-reviewer` in whole-plugin mode (Full review, no named subset) → the claim-graph-
  wide contradiction/circularity/broken-target findings a per-component scoped call can't see
- `plugin-validator` in its default Full-review mode → structural/manifest findings

## Scoped Mode

For a declared component set covering more than one component — a scope manifest's
`included` list, or an explicit multi-component list the caller names directly — which may
span more than one plugin (e.g. a `changed`/`named` scope touching both `plugin-devkit` and
`codex-kit` on the same branch):

1. **Per-component dispatch** — for each component in the list, dispatch the Component Mode
   set above (same reviewers, same rules) — excluding `dependency-reviewer` and
   `authority-reviewer`, same reasoning as Plugin Mode above: their per-component Full
   review adds nothing the whole-scope dispatch below doesn't already cover — batched
   across all components in parallel.
2. **Whole-scope reviewers, run once across the entire named list** (not once per component,
   not once per plugin). Each of these already accepts an arbitrary named-component list per
   its own agent definition — a cross-plugin list is not a new capability for them, only for
   this skill's own orchestration of them:
   - `activation-reviewer` — pass the full cross-plugin component list; cross-component
     overlap findings
   - `consistency-reviewer` — pass the full cross-plugin component list; drift/duplication
     findings
   - `dependency-reviewer` — Full review, named subset = the full cross-plugin component
     list (the graph-wide cycle/bidirectional/broken-target check, bounded to exactly this
     scope rather than an unbounded whole-plugin sweep)
   - `authority-reviewer` — Full review, named subset = the full cross-plugin component list
     (the claim-graph-wide contradiction/circularity/broken-target check, bounded to exactly
     this scope rather than an unbounded whole-plugin sweep)
3. **`plugin-validator`, once per distinct plugin touched.** `plugin-validator` validates one
   plugin's manifest and directory structure at a time — it has no cross-plugin mode. Group
   the component list by owning plugin (the `plugins/<name>/` path segment each component
   resolves under), and dispatch one Full-review `plugin-validator` call per distinct plugin
   found. Never dispatch it once across the whole cross-plugin scope, and never skip a
   touched plugin just because only one of its components is in scope — the
   manifest/structure/security checks are inherently whole-plugin, not per-component, the
   same rule Plugin Mode already applies to a single plugin.

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
