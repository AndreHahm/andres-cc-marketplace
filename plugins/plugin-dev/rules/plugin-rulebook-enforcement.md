# Plugin Rulebook Enforcement

## Mandatory Compliance Triggers

Run the `plugin-rulebook` skill **before finalizing** any operation that creates, modifies, renames, or removes a plugin component. This applies to:

| Component type | Covered operations |
|---|---|
| Skill (SKILL.md + supporting files) | create, modify, rename, split, merge, delete |
| Agent (agent `.md` file) | create, modify, rename, delete |
| Command (command `.md` file) | create, modify, rename, delete |
| Hook (hook config + scripts) | create, modify, rename, delete |
| Workflow skill (a skill that orchestrates other components rather than performing one focused task) | create, modify, rename, split, merge, delete |
| Rule (`.claude/rules/*.md` files) | create, modify, merge, apply, extract, delete |

"Before finalizing" means: after the **last** modification in a creation or editing sequence, before reporting the work as done to the user. Intermediate edits within a single session do not each require a separate check — only the final state does.

> **Not in scope:** Files in `.claude/output/` (generated artifacts), build outputs, and other non-component files are not subject to rulebook enforcement.

## Rule Conflict Resolution

When the active `plugin-rulebook` (as configured in `.claude/skills/plugin-rulebook/assets/settings.json`) conflicts with any other project rule, CLAUDE.md instruction, or inline user preference, **the rulebook wins for plugin component decisions**. The priority stack is:

1. Active rulebook rules (R1–R26, enabled in `settings.json`) — highest authority for component structure, naming, and formatting decisions
2. CLAUDE.md project instructions
3. Inline user preferences for the current session

This priority applies to plugin component decisions only. CLAUDE.md behavioral guidelines (simplicity, surgical changes, think before coding) continue to govern how those decisions are implemented.

Exception: a user may explicitly override a specific rulebook rule in the current session by naming it (e.g., "ignore R7 for this file"). Single-rule overrides are allowed; blanket "skip the rulebook" overrides are not.

## Compliance Procedure

1. Identify the component type from the table above.
2. Invoke `plugin-rulebook` via `Skill(plugin-rulebook)` targeting the component. Example: "validate `.claude/skills/my-skill/SKILL.md` (type: skill) for rulebook compliance".
3. Act on the compliance report:
   - **FAIL (REQUIRED rule)** — fix before marking the task done.
   - **ADVISORY (SUGGESTED rule)** — surface to the user; proceed if they accept.
   - **PASS** — no action needed.
4. Re-run after applying fixes until the report shows no FAIL findings.

**Post-commit verification (required):** after every `git commit` — including each commit in a multi-commit batch — run `git status` (expect a clean tree for the paths just committed) and `git show --stat` (or `git diff --stat <prev>..<commit>`) against the intended file list before considering that commit final. A batched `git add` with multiple pathspecs silently stages nothing at all if even one pathspec fails to match (e.g. a path already moved by a prior `git rm`) — the commit then succeeds but is missing files, with no error at commit time. This check is what catches that failure mode; do not skip it because the `git add`/`git commit` commands themselves reported success.

**Batch mode:** When one session's work applies the same rule change across N components (e.g., rolling a new rule out to multiple skills), a single `Skill(plugin-rulebook)` invocation satisfies "before finalizing" for all N — provided the resulting compliance report enumerates each component by name with its own PASS/ADVISORY/FAIL line, not one blanket verdict. Asserting compliance from memory, without an actual tool invocation covering the named components, does not satisfy this rule — the check must be an executed `Skill(plugin-rulebook)` call, not a recollection of what an earlier call found.

## Duplicate Fact Sweep Trigger (R20)

**Trigger:** any change to a canonical value in `plugin-rulebook`'s `assets/settings.json` — an R13/R18/R21/R22 threshold, an enum list (e.g. `agent.color.valid_values`), or a forbidden-field list.

**Procedure:** this is not a separate blocking gate — it's an explicit line item on the same "before finalizing" check in the Compliance Procedure above:
1. Grep the plugin tree for the previous value before finalizing.
2. Update every sibling occurrence found, or record the divergence as an intentional exception.
3. Report swept occurrences (or "none found") alongside the R20 PASS/FAIL line in the compliance report.

**Single-pass, whole-file requirement:** when converting a component (or a set of sibling components) from an old convention to a new one, grep each affected file's **entire content in one pass** — frontmatter and body and any templates/examples it contains — rather than fixing frontmatter first and re-checking body instructions in a follow-up round. A convention conversion isn't done until both frontmatter and body agree; splitting the check across multiple rounds is what let a body-instruction contradiction survive an earlier "fixed" frontmatter in this plugin's own agent-creator.md.

**Whole-tree sweep order:** the initial grep for a convention change must cover `agents/`, `commands/`, `skills/`, and `rules/` together, in the same first pass — not `agents/` first with the rest found later by a catch-all cleanup. This plugin's own `<example>`-block removal found `commands/create-plugin.md`'s testing checklist and `agent-development/scripts/validate-agent.sh`'s heuristic stale only in a final sweep, after `agents/` had already been treated as done. Run one repo-wide grep for the old convention's marker string across all four directories before declaring any of them finished.

**Exception — respect R19:** Do not flag the `.claude/` ↔ `plugins/plugin-dev/` mirror duplication itself as stale-value drift (see R19's in-development-mirror exception in `plugin-rulebook/SKILL.md`) — that duplication is structurally expected, not a fact that has diverged, as long as both copies stay identical. R20 targets facts that have drifted *between independently-worded restatements* (e.g. three skills each hand-writing the same character limit), not the intentional mirror pattern itself.

**Keeping plugin development possible:** this trigger fires at "before finalizing," the same checkpoint as every other rule here — not on every intermediate edit. Editing a canonical value mid-task does not require an immediate repo-wide sweep; only the final state before reporting the work as done does. This matches the existing "intermediate edits within a single session do not each require a separate check" principle above.

## Backing Hooks for Destructive Actions

Manual `plugin-rulebook` invocation is a policy gate, not a runtime guardrail. If a component change adds a destructive or irreversible action (e.g., a hook that deletes or overwrites), the enforcement rule MUST also require a backing hook — a textual rule alone is not sufficient enforcement. For plugins shipped as a team tool, pair this manual check with the live PostToolUse validation hook described in the `hook-development` skill.

## Upstream Source Verification

Plugin-rulebook rules that trace back to an official Claude Code doc are tracked, classified, and freshness-checked by the `upstream-sources-registry` skill — not by a rulebook-owned audit procedure. When a tracked source changes, `find-dev-rule`/`verify-dev-rules`/`update-dev-rule` (which consult that registry instead of a blind `WebSearch`) surface the gap through their existing classification (`OUTDATED`/`MISSING`/`CONFLICT`) rather than a rulebook-specific "audit mode."

**Intentional divergence:** if a plugin-rulebook rule should knowingly differ from what an official source currently says (a deliberate policy choice, not a defect), record it via `verify-dev-rules`'s Exclusion mechanism (its Step 2) rather than a separate rulebook-specific decision log — `verify-dev-rules` already treats a target's prior exclusions as binding across runs (its Step 3), so a decision recorded once is not re-litigated on the next check.

**Trigger:** run `verify-dev-rules --level component --name plugin-rulebook` (or the equivalent whole-plugin invocation) whenever a tracked upstream source changes, or monthly at minimum — same cadence as before.

**Migrated history:** `.claude/plugin-rulebook-audit-decisions.md` is retained as the historical record of decisions made under the old mechanism. New decisions are recorded in `verify-dev-rules`'s own gap reports going forward — any decision in the old log still actively relevant should be re-recorded as an Excluded Candidate the next time `verify-dev-rules` runs against `plugin-rulebook`, so it isn't silently re-flagged as a fresh gap now that this section's old procedure no longer runs.
