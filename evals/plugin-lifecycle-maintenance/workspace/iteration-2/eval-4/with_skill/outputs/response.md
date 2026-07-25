# Response: "I just ran a plugin-comparison between plugin-foo and an external plugin, and found some real deltas I want to act on"

## 1. Matching workflow: `workflows/enhance-a-plugin.md`

This is the comparison-driven enhancement workflow, and it's the right match because the finding source is explicitly `plugin-comparison`, which is exactly what the user says they already ran.

Ruling out the other two:

- **`improve-a-plugin.md`** (retro-driven) is driven by `analyzing-sessions` findings from session behavior — the user didn't run a retro, they ran a comparison. Wrong finding source.
- **`self-upstream-plugin-devkit.md`** is scoped specifically to keeping `plugin-devkit`'s own rules current against official Claude Code docs, via the `/report-dev-rules` → `/verify-dev-rules` → `/plan-dev-rules` → `/implement-dev-rules` (bulk) or `/find-dev-rule` → `/update-dev-rule` (single-rule) command chains — not a `plugin-comparison` report. Wrong domain and wrong finding source.

The `SKILL.md` Quick Start table confirms this directly: `enhance-a-plugin.md` is "Comparison-driven: `plugin-comparison` finds gaps against another target, human picks, hand off to Fix."

Since the user has *already run* `plugin-comparison` (not asking this skill to run it), the workflow's Step 1 "Invoke `plugin-comparison`" action is effectively already satisfied — the workflow picks up from the existing written report at `.claude/output/plugin-comparison/comparison-<timestamp>.md`, presents the artifact link, and proceeds to Step 2 (Human Decides) rather than re-running the comparison from scratch.

## 2. Finding source

The finding source is the **`plugin-comparison` skill** — specifically its written report at `.claude/output/plugin-comparison/comparison-<timestamp>.md`. The workflow reads the report's "Unique to B", "Notable Differences", and "Recommendation" sections as the candidate deltas. (Exit criteria: if all three sections are empty — the two targets are equivalent — the workflow states this plainly and stops; here the user says they found "real deltas," so this exit path doesn't apply.)

## 3. After human approval: where the Fix hand-off goes and how

**Step 2 — Human Decides:** The report's "Unique to B", "Notable Differences", and "Recommendation" sections are presented, and the human picks which deltas to act on via `AskUserQuestion` (multiSelect) — "none of these, stop here" is a valid answer. Optionally, `enhancement-suggestor` (via `Agent`) can expand a chosen delta into a full WHAT/WHY/HOW plan first.

**Step 3 — Hand Off to Fix:** The approved deltas are reformatted into a list matching `plugin-grader`'s real `prioritized_next_steps` schema (`rank`, `action`, `dimension` if applicable, `points_gain_estimate` as a rough estimate, `lifts_gate` always `null` since these didn't come from a real audit gate).

The hand-off mechanism is a `Skill` invocation of **`plugin-lifecycle-downstream`**, targeting the plugin being enhanced (plugin-foo), entering via its **documented external Phase 3 entry point** (see `plugin-lifecycle-downstream/workflows/run-qa-pipeline.md`, Phase 3's Entry condition) with the reformatted delta list — **skipping Phases 1-2** (Validate/Audit), since the findings already came from the comparison rather than needing a fresh `plugin-grader` audit. This skill never reimplements apply → re-validate → commit logic itself; it reuses `plugin-lifecycle-downstream`'s existing Fix phase machinery, including that phase's own commit confirmation.

Exit criteria for Step 3: downstream's Phase 3 reports all approved deltas applied and re-validated (fully or partially), with its own commit(s) already made.

**After that:**
- **Step 4 — Document:** `human-doc-reviewer` (via `Agent`) is run against plugin-foo's human-facing docs (README, CHANGELOG, etc.) to check whether the change needs a documentation update — applied fixes are committed **separately** from the core fix commit(s) from Step 3.
- **Step 5 — Handover (optional):** Only if Step 4 changed anything, ask via `AskUserQuestion` whether to run a final downstream QA pass (a full Phases 1-2 Validate+Audit) to confirm the doc changes didn't break anything. Never auto-invoked without asking.
