# What the Document step does when plugin-documentation finds no gaps

Scenario: the core fix for plugin-foo has already landed and been committed (this is Step 3 in
`improve-a-plugin.md` / `enhance-a-plugin.md`, or the equivalent apply step in the other two
workflows). We're now at Step 4, "Document" — the shared step defined once in
`plugin-lifecycle-maintenance/SKILL.md` under "The Document Step (Shared Across All 4 Workflows)"
and reused verbatim by all four workflows.

## What happens

1. **Invoke `plugin-documentation` via `Skill`**, pointed at the plugin's human-facing docs
   (README.md, CHANGELOG.md, CONTRIBUTING.md, etc.), passing the specific list of changed claims
   from the core fix that just landed. This skill does the real work — it reads the plugin's
   actual current components as source of truth and decides whether any doc content needs to
   change.

2. **`plugin-documentation` owns the delta-vs-full QA decision internally.** The maintenance
   skill does **not** ask its own separate delta/full question before dispatching — that would
   ask the same question twice, since `plugin-documentation` already runs its own
   `human-doc-reviewer` QA pass and picks delta (small, enumerable change set) vs. full
   (large/structural change) on its own. Plugin-rulebook R26 is already satisfied by that
   internal gate.

3. **If `plugin-documentation` reports no documentation gaps / no update needed:** this is
   treated as **a normal, valid outcome — not a failure and not something to silently pass over**.
   The SKILL.md is explicit: *"'No update needed' is a common, valid outcome, not a failure."*
   The workflow must still **state this plainly to the user** rather than skip the step quietly.
   This is codified as its own test scenario (#6, "Document step, nothing to update") and its own
   quality gate in SKILL.md's Testing & Validation section: *"confirm 'no doc update needed' is
   presented as a normal outcome, not silently skipped without being stated."*

4. **No commit happens for the Document step in this case.** The separate-commit discipline
   ("Stage and commit any kept doc changes separately from the core fix's own commit(s)") only
   applies when there *is* a kept doc change. With nothing to keep, there is nothing to stage or
   commit — the core fix's commit (already made in Step 3) remains the only commit from this
   pass.

5. **Downstream effect on Step 5 (Handover, in `improve-a-plugin.md`) / equivalent optional
   follow-up steps:** those steps are explicitly gated on "if Step 4 applied any doc change."
   Since no doc change was applied here, the optional final downstream QA pass is **skipped** —
   `improve-a-plugin.md` Step 5 says outright: *"If Step 4 made no changes, skip this step —
   there is nothing new to QA."* The same logic carries to the analogous optional-handover point
   in the other three workflows.

## Net result for this scenario

- Core fix: already committed (given).
- Document step: `plugin-documentation` invoked, reports no gaps -> maintenance skill states
  "no documentation update needed" to the user as the outcome of this step.
- No second (doc) commit is made.
- No `AskUserQuestion` "keep/revise/discard" prompt is needed since there's no authored diff to
  decide on — that question only applies when `plugin-documentation` actually produces changes.
- Any optional handover/final-QA offer tied to "Step 4 applied changes" is skipped, since no doc
  changes were applied.
- The workflow ends cleanly here: core fix committed, docs confirmed current, nothing further
  queued.

## Source references

- `.claude/skills/plugin-lifecycle-maintenance/SKILL.md` — "The Document Step (Shared Across All
  4 Workflows)" section (lines ~57-59); Testing & Validation scenario 6 and its quality gate
  (lines ~82, ~89).
- `.claude/skills/plugin-lifecycle-maintenance/workflows/improve-a-plugin.md` — Step 4 (Document,
  line ~37-39) and Step 5 (Handover, Optional, line ~41-45), showing the "no changes -> skip"
  chaining.
- Mirrored copy: `plugins/plugin-devkit/skills/plugin-lifecycle-maintenance/SKILL.md` and its
  `workflows/improve-a-plugin.md` (same content, per the plugin's intentional in-development
  mirror between `.claude/` and `plugins/plugin-devkit/`).
