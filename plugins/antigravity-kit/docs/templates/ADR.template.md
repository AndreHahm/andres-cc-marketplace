<!--
ADR TEMPLATE — usage notes (delete this comment block when instantiating)

Purpose: capture a single architectural decision and its context, alternatives,
and consequences. One ADR = one decision. Do not bundle multiple decisions.

Naming convention for instantiated files:
  docs/adr/ADR-<number>-<kebab-case-title>.md
  e.g. docs/adr/ADR-001-hub-path-resolution-strategy.md
       docs/adr/ADR-015-token-budget-enforcement-layer.md

Numbering: zero-padded, monotonically increasing. Never reuse or renumber
existing ADRs. If a decision is superseded, mark its status as "Superseded by
ADR-<N>" and create a new ADR that references the old one.

Status values:
  Proposed   — drafted, awaiting review/approval
  Accepted   — approved and in effect
  Deprecated — no longer in effect; not yet superseded
  Superseded — replaced by a later ADR (name the successor)

Keep ADRs immutable once Accepted. If context changes, write a new ADR that
supersedes the old one rather than editing the accepted record.
-->

---
title: "ADR-<number>: <Decision Title>"
adr_number: "<number>"
status: Proposed|Accepted|Deprecated|Superseded
decided_date: YYYY-MM-DD
superseded_by: "<ADR-NNN, or blank>"
supersedes: "<ADR-NNN, or blank>"
tags: [architecture, <domain-tag>]
---

# ADR-<number>: <Decision Title>

> One-line summary of the decision.

## Context

Describe the forces at play — technical, political, social, project-specific.
What problem are we solving? What constraints exist? What is the current state
that motivates this decision?

- **Problem statement**: <...>
- **Constraints**: <technical limits, deadlines, dependencies, compatibility>
- **Assumptions**: <what we believe to be true but haven't verified>

## Decision

State the decision clearly and concisely. What are we doing? Be specific enough
that someone unfamiliar with the discussion can understand the chosen path.

**We will <action>**.

### Rationale

Why this option over the alternatives? What tipped the balance?

- **<Reason 1>**: <...>
- **<Reason 2>**: <...>

## Alternatives Considered

For each alternative, describe it, list pros/cons, and explain why it was
rejected.

### Alternative A: <name>

- **Description**: <...>
- **Pros**: <...>
- **Cons**: <...>
- **Why rejected**: <...>

### Alternative B: <name>

- **Description**: <...>
- **Pros**: <...>
- **Cons**: <...>
- **Why rejected**: <...>

## Consequences

What follows from this decision? Be honest about trade-offs.

- **Positive consequences**: <what we gain>
- **Negative consequences**: <what we accept or work around>
- **Neutral consequences**: <side effects that are neither good nor bad but worth noting>
- **Follow-up actions**: <tasks, migrations, documentation, or future ADRs triggered by this decision>

## Compliance

How do we verify this decision is being followed?

- **Verification method**: <review checklist, test, lint rule, CI gate, etc.>
- **Owner**: <role or person accountable for enforcement>

## References

- [Related ADR](../adr/ADR-NNN-title.md) — <relationship: supersedes, complements, conflicts>
- `<relevant file path>` — <how it relates>
- [External link](<url>) — <what it informed>

## Revision History

| Date | Author | Status | Change |
|---|---|---|---|
| YYYY-MM-DD | <name> | Proposed | Initial draft |
