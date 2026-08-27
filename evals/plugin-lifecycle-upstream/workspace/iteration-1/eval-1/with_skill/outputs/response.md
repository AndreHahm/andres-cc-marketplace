# What Gate 1 does, and what runs next

## Gate 1

Gate 1 is the checkpoint at the end of Phase 1 (Conceive). With the Conception Brief now written, Gate 1:

1. **Presents the artifact link first**, as its own line, before any summary:
   ```
   📄 Conception Brief written: `.claude/output/plugin-conception/<concept-slug>-<timestamp>.md`
   ```
2. **Presents the brief's classification and rationale.**
3. **Branches on the classification:**
   - **Classification = Create** (this case): ask via `AskUserQuestion` — proceed to Ideate / revise the concept / stop. The pipeline does not proceed until the user explicitly approves. On approval, the light Conception Brief becomes Phase 2 (Ideate)'s input, exactly as a rough idea would be.
   - **Classification = anything else** (Enhance, Repair, Consolidate, Reposition, Retain, Reject/Defer): the pipeline is creation-only and stops at Gate 1 — it states `plugin-conception`'s own hand-off target plainly (`plugin-planning` directly, `plugin-lifecycle-downstream`'s Phase 8 Consolidated Fix, or a clean stop with rationale) and points the user there instead of proceeding.

Since this run's Conception Brief has **Concept type = Create**, Gate 1 takes the first branch: present the brief link + classification/rationale, then ask (via `AskUserQuestion`) proceed to Ideate / revise / stop, and wait for explicit approval before advancing.

## Next phase

**Phase 2: Ideate.** Once Gate 1 is approved, the pipeline invokes `plugin-ideation` (via `Skill`) — passing Phase 1's light Conception Brief as its input — and waits for the Concept Card to be written to `.claude/output/plugin-ideation/<slug>-<timestamp>.md`. That Concept Card (with its overlap classification of None or Partial) is what Gate 2 then presents for the next approval.

## Source

- `plugins/plugin-devkit/skills/plugin-lifecycle-upstream/SKILL.md` — "The Seven Phases" table and the "Conceive is a qualifier, not an interview" section (lines 69–83)
- `plugins/plugin-devkit/skills/plugin-lifecycle-upstream/workflows/design-a-plugin.md` — Phase 1 "GATE 1" block (lines 19–28) and Phase 2 "Actions"/entry criteria (lines 30–38)
