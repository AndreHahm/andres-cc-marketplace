# workmanagement-kit

The sole Notion/Linear access point for this repository. Notion owns knowledge and intent
(Ideas, Decisions, proposed Goals, research, reports, learning); Linear owns accepted strategy and
execution (Goals, Roadmaps, Projects, Milestones, Issues). Claude Code is the only agent that
mutates either system; Codex is a secondary, read-only reviewer.

No other plugin in this repository implements its own Notion or Linear connector. A plugin whose
own workflow produces something worth storing in Notion or acting on in Linear (e.g. an output
report) routes it through this plugin's `plugin-integration-intake` skill instead.

## Plugin Target

- One governed access point for Notion/Linear, so no other plugin duplicates connector/approval
  logic.
- Every material action (creation, promotion, status change, closure) requires live, fresh
  approval — including when a request originates from another plugin's own workflow.
- Deliberate, approval-gated bridges between the two systems only; no background or automatic
  synchronization in either direction.
- Codex reviews transitions, closures, and ambiguous intake read-only; it never mutates Notion or
  Linear, on any path.

## Overview

`workmanagement-kit` provides:

- **`notion-knowledge-management`** — capture and manage Ideas, Decisions (with
  proposed/accepted/superseded/reversed states), proposed Goals, Notes, Research, Reports,
  Outcomes, and Learning in Notion.
- **`linear-work-management`** — read and update accepted Goals, Roadmaps, Projects, Milestones,
  and Issues in Linear under Linear's own authority.
- **`idea-to-implementation`** — deliberate, approval-gated promotion from Notion knowledge into
  an accepted Linear hierarchy.
- **`status-and-learning`** — deliberate, dated, explicitly non-live Linear-to-Notion progress
  summaries and outcome/learning capture.
- **`work-linking`** — stable cross-system links, authority labels, drift detection, and bounded
  repair between Notion and Linear.
- **`open-item-management`** — revalidation and disposition of open questions, decisions, and
  follow-ups; not every question becomes a Linear Issue.
- **`plugin-integration-intake`** — the sole host-invoked entry point another plugin's own
  workflow uses to submit content for Notion/Linear storage or action, under the same live
  approval gate as a direct user request.
- **`work-transition-reviewer`** and **`work-intake-classifier`** — read-only Codex reviewer
  personas. The standalone path (via the `.claude/agents` → `.codex/agents` export for direct
  Codex CLI use) is available now; the live path via `codex-kit`'s `codex-review-bridge` requires
  this plugin's own bridge-caller script, not yet built (see Status).

This plugin depends on `codex-kit` for the live Codex review path.

## Installation

Install from this marketplace the same way as any other plugin in this repository (see the
repository's own installation instructions). `codex-kit` must also be installed for the live
Codex review path to function; without it, a review is disclosed as unavailable rather than
silently skipped.

## Status

This is Wave 1 of a two-wave design (Wave 1: Notion/Linear foundation; Wave 2, not built here: a
later, additive Git/GitHub lifecycle bridge). Live Notion/Linear mutation requires the Foundational
Setup steps described in this plugin's design documents to be completed (connector installation,
workspace/team scoping, test scopes) before first live use.

Two further items are still open before this plugin is fully live:
- The Codex bridge-caller script that dispatches `work-transition-reviewer`/
  `work-intake-classifier` live is not yet built; both agents already work standalone via the
  `.codex/agents` export.
- `plugin-integration-intake`'s trust-boundary gate has not yet had its required
  `security-reviewer` pass (see that skill's own file for the specific checklist item).
