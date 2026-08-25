# Plugin Conception — Classification Run

**Idea submitted:** "Build a new skill that reviews a Claude Code skill's SKILL.md for quality and adherence to best practices."

Running `plugin-conception`, Entry Route A (from-scratch idea, no session evidence supplied). `$ARGUMENTS` is the idea itself, so it's treated directly per the skill's Route A instruction rather than re-asked.

---

## Step 1 — Normalize Intent and Evidence

| Field | Value |
|---|---|
| Problem / opportunity | No stated pain point beyond "I want this capability to exist" — the requester wants a way to check a SKILL.md against quality/best-practice standards. |
| Target user & scenario | A plugin author, after creating or editing a skill's SKILL.md, wanting a structured quality check before shipping. |
| Desired outcome | A report on the SKILL.md's quality and adherence to best practices. |
| Constraints / non-goals | None stated. |
| Adjacent component the requester believes exists | None named — requester did not check first. |

**Assumption (A1, labeled):** the requester has not verified whether this capability already exists in the marketplace. This assumption is exactly what Step 3 exists to test, so it is not resolved here — it's carried into the overlap check below.

No other evidence to normalize; nothing here is stale or second-hand, so no current-state reverification is needed at this step (that check applies to Route B evidence).

## Step 2 — Tentative Classification

Taken at face value, "build a new skill that does X" reads as **Create**. Per the skill's own instruction, this is provisional — Step 3's overlap check can revise it, and often does for exactly this shape of request (a plausible-sounding new idea that turns out to duplicate something already shipped).

## Step 3 — Check Overlap and Marketplace Fit (repository-metadata depth, run for real against this repo)

Searched plugin manifests, agent/skill descriptions, and lifecycle ownership across the marketplace for existing components that already review a skill's SKILL.md for quality/best-practice adherence.

| Candidate | Location | Relationship | Overlap | Evidence |
|---|---|---|---|---|
| `skill-reviewer` (agent) | `plugins/plugin-devkit/agents/skill-reviewer.md` (mirrored at `.claude/agents/skill-reviewer.md`) | Same capability | **Full** | Description: *"Review Claude Code skill quality and adherence to standards. Use this agent when the user has created or modified a skill and needs quality review... or wants to ensure a skill follows best practices. Trigger proactively after SKILL.md itself is created or modified."* This is a near word-for-word match to the submitted idea. Its body runs a 7-step pipeline: loads `plugin-rulebook` (R13/R18 thresholds) and `skill-development`'s rubric/checklist/content-guidelines/size-limits/design-patterns as the standards source, applies C1–C4 gatekeeper checks, scores Activation/Implementation (rubric.md), validates against the full checklist (including chain-violation, cross-skill overlap, workflow-pattern, tool-reconciliation, and anti-pattern checks), and emits either a narrative Battle Test Report or structured YAML. |
| `plugin-grader` (skill) | `plugins/plugin-devkit/skills/plugin-grader/` | Consumer / superset | Partial (as a target-type mode, it fully subsumes the idea) | Grades a skill (skill is an explicitly gradeable target type) against 12 weighted dimensions — structure, content quality, rule compliance, completeness, maintainability, robustness, simplicity, testing, uniqueness, safety, efficiency, actionability — with hard gates, SWOT, and prioritized next steps. Broader than "quality and best-practice adherence" alone, but covers it entirely as a subset. |
| `skill-refiner-interactive` (skill) | `plugins/plugin-devkit/skills/skill-refiner-interactive/` | Direct wrapper | Full | Own description states it wraps `skill-reviewer` in Validation mode and then interactively applies fixes — i.e., it already packages this exact review capability into an interactive workflow. |
| `plugin-rulebook` (skill) | `plugins/plugin-devkit/skills/plugin-rulebook/` | Overlapping sub-domain | Partial | Owns the R1–R27 naming/language/formatting/tool-scoping compliance axis specifically, which `skill-reviewer`'s Step 1 already loads and defers to for size thresholds (R13/R18). |
| `skill-development` (skill) | `plugins/plugin-devkit/skills/skill-development/` | Standards source | Partial | Owns the rubric, checklist, and content-guidelines that `skill-reviewer` reads as its source of truth — the "best practices" the idea wants checked are already codified here. |

**Overlap verdict: Full.** The exact capability described — reviewing a SKILL.md for quality and adherence to best practices, triggered on skill creation/modification — already exists, is actively maintained, is the *stated primary trigger* of an existing component (`skill-reviewer`), and is additionally reachable through two more layers (`skill-refiner-interactive` for interactive fix-review, `plugin-grader` for a broader scored assessment). Per the skill's Step 3 table, Full overlap means "a Create outcome is very unlikely to survive this finding" and the classification shifts toward **Retain**.

**Not done here** (per the skill's explicit scope limit): activation-trigger overlap analysis between these candidates, cross-component reference tracing, or naming-candidate validation — that's `plugin-ideation`'s job if this were still headed toward Create, which it is not.

## Step 2 (revised) — Final Classification

**Classification: Retain.**

**Rationale:** the marketplace already ships a component whose entire job is exactly this idea — `skill-reviewer` reviews a SKILL.md for quality and best-practice adherence, is triggered proactively on SKILL.md creation/modification, scores it against a maintained rubric, and reports Critical/Major/Minor findings. `skill-refiner-interactive` already wraps it for an interactive fix loop, and `plugin-grader` already offers a broader scored version when a single skill is the target. Building a new skill to do the same thing would duplicate all three, fragment the "what counts as best practice" source of truth (which currently lives in one place, `skill-development`'s rubric/checklist), and create exactly the kind of overlap `plugin-rulebook`'s cross-skill overlap check would flag on the new skill's own first review.

**Alternatives considered:**

| Alternative | Benefit | Cost / limitation | Decision |
|---|---|---|---|
| Create a new skill as requested | Matches the literal ask | Duplicates `skill-reviewer`/`skill-refiner-interactive`/`plugin-grader`; fragments the standards source of truth | Rejected |
| Enhance `skill-reviewer` if some specific check is actually missing | Keeps one source of truth | No missing check was named by the requester — nothing to enhance without a concrete gap | Not applicable; no gap identified |
| Retain — use what exists | No duplicate work; capability already ships today | Requester must be pointed at the existing tool instead of getting a new one | **Selected** |

Per the skill's own **Stop Conditions** and **Testing & Validation** scenario 7 (Retain/no-work outcome), a clean stop here is a valid, complete result and does not require writing a Conception Brief file — there is no implementation to define, no scope/baseline/plan to hand off, and no marketplace placement decision to make. The rationale above is the deliverable.

## Step 7 — Decision Point

Per the skill's Step 7, this decision is normally presented via `AskUserQuestion` (approve and proceed / revise / merge / defer / reject-or-retain) before any hand-off. This test environment has no `AskUserQuestion` tool available, so that checkpoint is stated here explicitly instead of silently skipped, per this repo's own disclosure rule for un-fired gates:

> **Decision needed from you:** Retain — no new skill needed. Would you like to:
> 1. **Accept Retain** — use `skill-reviewer` (full review), `skill-refiner-interactive` (interactive fix loop), or `plugin-grader` (broader 12-dimension score) instead, whichever matches how you want to invoke it.
> 2. **Revise** — if there's a specific check `skill-reviewer` doesn't do today that you need, name it and this reclassifies as Enhance.
> 3. **Reject this classification** — if you disagree that the overlap is Full, say why and Step 3 can be re-run with the missing distinction.

No downstream hand-off is invoked (Retain routes to "Stop with rationale," not to `plugin-ideation` or `plugin-planning`), and none has been triggered here, consistent with the skill's own rule that only an approved concept proceeds and this skill never auto-applies a finding.

---

**Summary:** Classification = **Retain**. Full overlap found against `skill-reviewer` (agent), `skill-refiner-interactive` (skill), and `plugin-grader` (skill), all in `plugin-devkit`. No Conception Brief written (Retain/no-work outcome). No downstream hand-off invoked. Awaiting the requester's decision on the Step 7 question above.
