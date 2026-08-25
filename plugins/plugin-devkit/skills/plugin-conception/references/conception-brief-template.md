# [Concept Name] Conception Brief

> Delete all authoring instructions in blockquotes before approval. Replace every bracketed field. Use
> `Not applicable — <reason>` only where the template explicitly permits it.
>
> **Depth is proportional to classification.** This document has 12 top-level sections. A **Create**
> classification hands off to `plugin-ideation`, which owns the interview, deep overlap search, and
> naming — this brief stays light. Fill in: Metadata, Executive Concept, Evidence and Assumptions,
> Classification, Marketplace Integration (Step 3's shallow overlap check runs for every classification,
> including Create — its result lives here regardless), and Decision and Handoff. Mark as
> `Not applicable — Create classification, handed to plugin-ideation`: Scope and Boundaries,
> Existing-Component Baseline, and Implementation Plan. Mark Workflow as not applicable unless the
> concept itself genuinely coordinates 3+ dependent states (rare for a Create outcome, but not
> impossible). Fill in Risks and Mitigations only if a relevant risk survived the shallow check —
> otherwise mark it not applicable too. In Acceptance Criteria, fill in the "Conception readiness"
> checklist but mark "Eventual implementation success" as
> `Not applicable — plugin-ideation/plugin-planning own these criteria once the concept is defined`.
> Every other classification (Enhance, Repair, Consolidate, Reposition) fills in every section below in
> full, since no downstream skill currently does that depth of analysis for those paths.

## Metadata

| Field | Value |
|---|---|
| Status | Draft / Approved / Deferred / Rejected / Retained / Superseded (a later approved brief replaces this one for the same target) |
| Concept type | Create / Enhance / Repair / Consolidate / Reposition / Retain / Reject-Defer |
| Target type | Plugin / Skill / Agent / Command / Hook / Rule / Multi-component workflow |
| Target | [New provisional name or existing component path] |
| Marketplace owner | [Existing `<domain>-kit` or `<domain>-devkit`, proposed new plugin, or undecided with decision owner] |
| Entry route | From scratch / Recent-session evidence |
| Intake source | [Path to the request, session-evidence source, or report that seeded this concept] |
| Author | [Person or agent] |
| Created | [UTC timestamp] |
| Last verified | [UTC timestamp] |
| Decision owner | [Person or role] |

## Executive Concept

### Problem or opportunity

[Describe the user-visible problem or opportunity in concrete terms.]

### Target user and situation

[Identify who encounters it and the specific situation in which it occurs.]

### Value proposition

[One sentence: This concept helps <user> achieve <outcome> by <capability>.]

### Desired outcome

[Describe the observable result, not the proposed implementation.]

## Evidence and Assumptions

> For a from-scratch concept, evidence may be user research, repository inspection, analogous
> components, or explicitly labeled assumptions. For session-derived concepts, cite the source
> artifact or transcript and record current-state reverification.

### Evidence

| ID | Observation | Source | Current-state verification | Status |
|---|---|---|---|---|
| E1 | [Observed fact] | [Path, session, report, or user statement] | [How and when it was rechecked] | Valid / Stale / Resolved / Inconclusive |

### Assumptions

| ID | Assumption | Why it is necessary | Validation method | Decision gate |
|---|---|---|---|---|
| A1 | [Unverified belief] | [Why work cannot proceed without it] | [How it will be tested] | Conception / Planning / Design / Build |

### Evidence synthesis

[Explain the underlying need. Distinguish it from symptoms and discard stale or duplicate observations.]

## Classification

### Selected classification

[Create / Enhance / Repair / Consolidate / Reposition / Retain / Reject-Defer]

### Rationale

[Explain why this classification fits after current-state and overlap checks.]

### Alternatives considered

| Alternative | Benefit | Cost or limitation | Decision |
|---|---|---|---|
| [Alternative] | [Benefit] | [Tradeoff] | Selected / Rejected / Deferred |

## Scope and Boundaries

> Required for Enhance, Repair, Consolidate, and Reposition. For a Create classification, write
> `Not applicable — Create classification, handed to plugin-ideation` and remove the remaining
> subsections in this section.

### In scope

- [Capability or behavior]

### Non-goals

- [Explicitly excluded capability or responsibility]

### Constraints

- [Technical, marketplace, compatibility, dependency, permission, or process constraint]

### Success signals

- [Observable signal that the user outcome improved]

## Existing-Component Baseline

> Required for Enhance, Repair, Consolidate, and Reposition. For a Create classification, write
> `Not applicable — Create classification, handed to plugin-ideation` and remove the remaining
> subsections in this section.

### Behavior to preserve

- [Existing contract, trigger, output, integration, or compatibility guarantee]

### Verified deficiency

[Describe the gap between the baseline and required behavior, with evidence IDs.]

### Proposed delta

[State the smallest behavioral or structural change that closes the gap.]

### Affected surfaces

| Surface | Current behavior | Expected effect | Compatibility requirement |
|---|---|---|---|
| [Caller, trigger, docs, eval, workflow, dependency] | [Baseline] | [Change] | [Must remain compatible or migration needed] |

### Rejection or rollback conditions

- [Condition under which the enhancement should not proceed or should be reverted]

## Marketplace Integration

### Overlap check

> This check stays at repository-metadata depth (plugin manifests, component descriptions) — just
> enough to confirm or revise the classification above. It is not the deep, per-component,
> name-blocking search `plugin-ideation` runs for Create outcomes; do not duplicate that search here.

| Candidate or neighbor | Location | Relationship | Overlap | Required action |
|---|---|---|---|---|
| [Plugin/component] | [Path] | [Same, adjacent, dependency, consumer] | None / Partial / Full | Create / Extend / Compose / Consolidate / Stop |

### Placement decision

[Explain why the capability belongs in the selected plugin and functional group.]

### Provisional naming

> Not applicable for a Create classification — this brief never proposes a name; that's
> `plugin-ideation` Step 4's job. Fill in only for Enhance/Repair/Consolidate/Reposition, and only
> when the work implies a genuinely new component name (e.g. a Reposition into a differently-named
> group).

| Item | Proposed name | Convention check | Collision check |
|---|---|---|---|
| Plugin or component | [kebab-case name] | [Result] | [Result] |

> Plugin names must follow the marketplace convention `<domain>-kit` or `<domain>-devkit`, with
> exactly one hyphen immediately before the suffix.

### Dependencies and consumers

| Relationship | Component | Contract or artifact exchanged |
|---|---|---|
| Depends on / Consumed by | [Component] | [Input, output, schema, or behavior] |

### Trigger and responsibility boundaries

[State how users reach this capability and how its activation or responsibility differs from adjacent
components.]

### Conditional specialist reviews

| Review | Needed? | Reason | Result or planned gate |
|---|---|---|---|
| Activation overlap | Yes / No | [Reason] | [Result or gate] |
| Cross-component consistency | Yes / No | [Reason] | [Result or gate] |
| Permission impact | Yes / No | [Reason] | [Result or gate] |
| Deep inspection/comparison | Yes / No | [Reason] | [Result or gate] |

## Implementation Plan

> For a Create classification, write
> `Not applicable — Create classification; plugin-planning owns this after plugin-ideation completes`
> and remove the remaining subsections in this section. Otherwise, define reviewable work packages —
> detailed prompts, scripts, schemas, and line-level edits still belong in the subsequent planning or
> design artifact.

### Target file map

| Action | Path | Responsibility |
|---|---|---|
| Create / Modify / Remove | [Exact proposed path] | [Why this file changes] |

### Work packages

#### Work package 1: [Name]

**Goal:** [Independently reviewable outcome]

**Files/components:**

- [Create/modify path or component]

**Implementation outline:**

1. [Ordered action]
2. [Ordered action]

**Verification:**

- [Concrete test, evaluation, review, or inspection and its passing condition]

**Dependencies:** [Earlier work package or `None`]

### Recommended execution order

1. [Work package and reason for ordering]

### Test and evaluation strategy

| Requirement | Test or evaluation | Expected result | Evidence artifact |
|---|---|---|---|
| [Acceptance requirement] | [Scenario/command/review] | [Passing condition] | [Path or report] |

### Documentation impact

- [Human-facing or agent-facing documentation that must change, or `No documentation change
  expected — <reason>`]

### Commit strategy

- [Reviewable behavioral commit boundary]
- [Separate documentation-only boundary when required]

## Workflow

> Required only when the concept coordinates three or more dependent states, gates, or handoffs.
> Otherwise replace this entire section with `## Workflow` followed by `Not applicable — <reason>`.

### Entry conditions

- [Condition]

### Flow

| Stage | Input | Action | Output | Human gate | Downstream owner |
|---|---|---|---|---|---|
| [Stage] | [Artifact/state] | [Action] | [Artifact/state] | [Decision or None] | [Skill/workflow that receives this stage's output] |

### Stop, retry, and resume behavior

- **Stop:** [Clean stop conditions and recorded rationale]
- **Retry:** [Retryable failures and limit/owner]
- **Resume:** [Artifact and state from which processing resumes]

### Completion criteria

- [Condition proving the workflow has completed]

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation | Owner/gate |
|---|---|---|---|---|
| [Risk] | Low / Medium / High | Low / Medium / High | [Specific mitigation] | [Owner or phase] |

## Acceptance Criteria

### Conception readiness

- [ ] The problem, user, situation, and outcome are concrete.
- [ ] Evidence is cited and current, or assumptions are labeled with validation gates.
- [ ] Classification and marketplace placement are justified.
- [ ] Overlap is checked before naming and implementation planning.
- [ ] Scope, non-goals, and compatibility requirements are explicit.
- [ ] Work packages name target files/components and verification conditions.
- [ ] Workflow content is complete or explicitly not applicable.
- [ ] No unresolved placeholders remain.

### Eventual implementation success

> For a Create classification, write
> `Not applicable — plugin-ideation/plugin-planning own these criteria once the concept is defined`.

- [ ] [Observable behavior or quality criterion]
- [ ] [Integration or compatibility criterion]
- [ ] [Test/evaluation/documentation criterion]

## Decision and Handoff

### Decision

[Approve / Revise / Merge / Defer / Reject / Retain]

### Decision rationale

[Record why the decision was made.]

### Open decisions

| Decision | Owner | Required by gate | Options or constraint |
|---|---|---|---|
| [Question that legitimately remains] | [Owner] | Planning / Design / Build | [Bounded choice] |

### Handoff

| Field | Value |
|---|---|
| Downstream route | plugin-ideation (Create) / plugin-planning (Enhance, Consolidate, Reposition needing new components) / Fix — Phase 8 Consolidated Fix (Repair, or Enhance/Consolidate/Reposition with no new components) / Stop |
| Receiving component | [Skill or workflow] |
| Primary artifact | [This Conception Brief path] |
| Supporting artifacts | [Paths or None] |
| Resume instruction | [Where and how the next session resumes] |
