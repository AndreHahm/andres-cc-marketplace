# Plugin Conception — skill-baz over-broad `Bash(git:*)` grant

## Route

Entry Route B (recent-session evidence): the evidence is an already-accepted `plugin-rulebook-checker`
finding, not a from-scratch idea, so this runs the evidence-handling path (`references/evidence-routing.md`),
not Route A's interview.

## Step 1 — Normalize intent and evidence

- **Observation:** `skill-baz`'s `allowed-tools` frontmatter grants `Bash(git:*)` (any git subcommand),
  but the SKILL.md body never invokes any `git` command at all.
- **Source:** an already-accepted `plugin-rulebook-checker` finding (least-privilege tool-scoping
  violation — the grant is broader than anything the skill's own instructions actually use).
- **Current-state verification:** not independently re-run here — the finding is stated as already
  accepted, which this skill treats as the recheck already having happened at acceptance time. If that
  hasn't actually been re-verified against the current SKILL.md body, do that before Fix picks this up.
- **Underlying need vs. symptom:** the symptom is the stale/never-used `git:*` wildcard; the underlying
  need is that the grant should track the specific subcommands the skill actually calls (least privilege).
- **Constraint:** the fix is already fully known and narrowly scoped — replace `Bash(git:*)` with the
  exact subcommand allowlist matching real usage (e.g. `Bash(git status:*) Bash(git log:*)` or whatever
  the body's real Bash calls are) — no design decision remains open.

## Step 2 — Classify

**Classification: Repair** — the over-broad grant contradicts the marketplace's tool-scoping contract
(a component's `allowed-tools` should reflect actual usage, not a wildcard convenience grant), and the fix
restores compliant behavior rather than adding anything new.

**Narrow-repair bypass applies.** Both bypass conditions are met:
- the fix is already known and narrowly scoped (swap one Bash subcommand grant for the specific
  subcommands actually used — a one-line frontmatter edit);
- the finding is already accepted (via `plugin-rulebook-checker`, not a fresh, contested claim).

Per SKILL.md Step 2: *"a Repair classification with an already-known, narrowly-scoped fix and an
already-accepted finding does not need the full brief (Steps 4-5) — record the classification and
evidence, then hand off directly to Fix."* Steps 4 (Define the Concept) and 5 (Shape the Implementation
Plan) are therefore **skipped** — there is no concept to define beyond what's already recorded above, and
no implementation plan to shape beyond the fix itself.

## Step 3 — Overlap check (shallow)

At repository-metadata depth: this is an in-place correction to `skill-baz`'s own frontmatter, not a new
or relocated capability, so there is no other plugin/component to check for overlap against.
**Overlap: None.** Step 2's classification holds.

## Step 7 — Decision and hand-off

- **Decision needed from you:** approve this Repair classification and proceed to Fix / revise / defer.
- **Recommended hand-off target:** `plugin-lifecycle-downstream`'s Phase 8 (Consolidated Fix) — per the
  classification table, Repair routes directly to Fix, bypassing `plugin-planning` since no new or
  restructured component is implied.
- **Standalone-invocation gate:** this skill was invoked directly (not nested inside
  `plugin-lifecycle-upstream`/`plugin-lifecycle-maintenance`), so per SKILL.md the hand-off is never
  invoked silently — it requires your explicit confirmation before Fix actually runs. Please confirm:
  **proceed to Phase 8 (Consolidated Fix) with this Repair record**, or say if you'd like to revise the
  scope first.

No Conception Brief file was written under `.claude/output/plugin-conception/` — the narrow-repair bypass
is explicitly meant to avoid adding brief-writing ceremony to a one-line fix; the record above (evidence,
classification, rationale, overlap result) is the complete artifact for this bypass path.

## Summary

| Field | Value |
|---|---|
| Classification | Repair (narrow-repair bypass) |
| Evidence | Already-accepted `plugin-rulebook-checker` finding: `skill-baz` grants `Bash(git:*)`, body uses no git command |
| Overlap | None |
| Steps skipped | 4 (Define the Concept), 5 (Shape the Implementation Plan) — bypass conditions met |
| Hand-off target | `plugin-lifecycle-downstream` Phase 8 — Consolidated Fix |
| Fix action | Narrow `allowed-tools`' `Bash(git:*)` grant to the specific git subcommands `skill-baz`'s body actually uses |
| Gate | Awaiting your confirmation to invoke the hand-off (standalone invocation — never invoked silently) |
