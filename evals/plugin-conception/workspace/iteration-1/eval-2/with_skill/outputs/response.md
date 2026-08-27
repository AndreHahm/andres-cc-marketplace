# plugin-conception — Response

**Task:** Recent session evidence (a completeness-reviewer finding) shows that plugin-foo's SKILL.md has
no documented Testing & Validation section, which causes reviewers to repeatedly flag it as unfinished.
Classify this and produce the appropriate brief.

**Skill used:** `plugins/plugin-devkit/skills/plugin-conception/SKILL.md` (Entry Route B — recent-session
evidence).

---

## What I did

1. **Entry Route B** — the intake is a completeness-reviewer finding, so I ran the shared normalize/
   classify/shallow-overlap core from the session-evidence side, per `references/evidence-routing.md`.

2. **Step 1 — Normalize.** Problem frame: plugin-foo's SKILL.md lacks a Testing & Validation section;
   `require-tests-for-behavior-changes.md` already treats that section as the accepted test-evidence
   mechanism for "Skill, most other cases"; its absence is why `completeness-reviewer` (whose scope
   explicitly covers "missing evidence of validation/testing/evaluation runs") keeps re-flagging plugin-foo
   across QA passes.

   Before treating the finding as promotable, I checked current repository state as Step 1 requires
   ("never rely on an unverified claim... check the current repository state instead of trusting a stale
   report"): a directory search (`plugins/plugin-foo*`) found **no plugin literally named `plugin-foo`** in
   this marketplace. Rather than silently fabricating a target or silently discarding the evidence, I
   recorded this as two explicit, labeled assumptions (A1: "plugin-foo" is a stand-in for a real target
   still to be named; A2: the SKILL.md in question belongs to one specific skill, since a plugin itself has
   no single SKILL.md) with a stated validation method and gate for each — consistent with CLAUDE.md's
   "state assumptions explicitly" and the skill's "label every assumption" instruction. This keeps the
   brief's Status as **Draft** rather than Approved until a decision owner confirms the real target.

3. **Step 2 — Classify.** **Enhance.** The target already exists and functions; nothing here contradicts a
   previously working contract (that would be Repair), and no new plugin/component is implied (that would
   be Create). Adding a missing, already-expected documentation section to an existing skill is the
   definition of Enhance. This is **not** eligible for the Step 2 narrow-repair bypass — that bypass only
   applies to a Repair classification, and this isn't Repair.

4. **Step 3 — Shallow overlap check.** Repository-metadata depth only: no other plugin/skill in the
   marketplace duplicates this specific gap; the classification holds as Enhance.

5. **Steps 4-6 — Full depth (not skipped).** Because this is Enhance, not Create, I did **not** take the
   Create shortcut. I filled in Scope and Boundaries, a populated Existing-Component Baseline (behavior to
   preserve, verified deficiency tied to evidence ID E1, proposed delta, affected surfaces, rollback
   conditions), full Marketplace Integration, and a full Implementation Plan (one work package, since the
   fix is a single-surface documentation addition). Workflow is marked not applicable with a one-sentence
   reason, since the concept doesn't coordinate 3+ dependent states/gates.

6. **Step 7 — Decision and hand-off.** The skill requires presenting the completed brief via
   `AskUserQuestion` before treating it as approved, and before invoking any hand-off target. The
   `AskUserQuestion` tool is not available in this environment, so I could not literally invoke it; per
   the skill's own "or otherwise" allowance I present the decision as text below instead of silently
   defaulting to Approved. The brief itself is written as **Draft**, with an explicit Decision section
   stating what's still open (A1/A2 target confirmation) and the two live open decisions, and its
   documented downstream route (Fix — `plugin-lifecycle-downstream` Phase 8, Consolidated Fix, per the
   Enhance/no-new-component row of Step 7's hand-off table) is recorded but **not invoked** — consistent
   with "this skill never auto-applies findings or silently turns evidence into a feature."

## Classification result

**Enhance** — preserve plugin-foo (or its resolved skill), add the missing Testing & Validation section.

## Conception Brief written

`.claude/output/plugin-conception/plugin-foo-testing-validation-section-2026-08-25T16-34-49Z.md`

(Absolute path:
`C:\Dev\Repos\andres-cc-marketplace\.claude\worktrees\plugin-conception\.claude\output\plugin-conception\plugin-foo-testing-validation-section-2026-08-25T16-34-49Z.md`)

This is the **full 12-section brief** (Metadata, Executive Concept, Evidence and Assumptions,
Classification, Scope and Boundaries, Existing-Component Baseline, Marketplace Integration, Implementation
Plan, Workflow [marked N/A with reason], Risks and Mitigations, Acceptance Criteria, Decision and Handoff)
— not the light Create variant, matching the Enhance/Repair/Consolidate/Reposition depth the skill
specifies.

**Existing-Component Baseline (populated), for reference:**

- **Behavior to preserve:** all of plugin-foo's current SKILL.md content stays unchanged — this is
  additive only.
- **Verified deficiency:** no Testing & Validation section exists (evidence E1), which
  `completeness-reviewer`'s own scope repeatedly flags.
- **Proposed delta:** add one new "## Testing & Validation" section (concrete scenarios, pass/fail
  criteria, quality-gates checklist) sized to plugin-foo's actual behavior.
- **Affected surfaces:** `completeness-reviewer` (flags cleared once added), the
  `plugin-rulebook-enforcement.md` before-finalizing gate (new compliance touchpoint), and
  `require-tests-for-behavior-changes.md` (defines the acceptance bar).
- **Rollback conditions:** if A1/A2 can't be resolved to a real target, or if the finding turns out to be
  stale (section already exists elsewhere), stop rather than proceed.

## Open items for the requester

1. Confirm which literal plugin/skill "plugin-foo" refers to (A1/A2 in the brief) — needed before this
   brief can move from Draft to Approved and before Fix begins.
2. Decide: proceed straight to Fix once A1/A2 are confirmed, or re-run `completeness-reviewer` first to
   reconfirm the finding is still current.

No hand-off was invoked — per Step 7, hand-off requires an explicit approval decision first, and that
decision is still open pending the above.
