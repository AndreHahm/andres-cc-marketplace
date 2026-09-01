# workmanagement-kit

The sole Notion/Linear access point for this repository. Notion owns knowledge and intent
(Ideas, Decisions, proposed Goals, Notes, Research, Reports, and Outcome/Learning records); Linear
owns accepted strategy and execution (Goals, Roadmaps, Projects, Milestones, Issues). Claude Code
is the only agent that mutates either system; Codex is a secondary, read-only reviewer.

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
  personas. Both the standalone path (via the `.claude/agents` → `.codex/agents` export for direct
  Codex CLI use) and the live path (via this plugin's own `scripts/bridge_caller.py`, dispatching
  through `codex-kit`'s `codex-review-bridge`) are built and live (see Status).

This plugin depends on `codex-kit` for the live Codex review path.

## Installation

Install from this marketplace the same way as any other plugin in this repository (see the
repository's own installation instructions). `codex-kit` must also be installed for the live
Codex review path to function; without it (or on a Codex dispatch failure), `scripts/bridge_caller.py`
returns the bridge's own typed failure rather than silently skipping the review — see Status for
the script's current known reliability caveat on Windows.

## Status

This is Wave 1 of a two-wave design (Wave 1: Notion/Linear foundation; Wave 2, not built here: a
later, additive Git/GitHub lifecycle bridge). Live Notion/Linear mutation requires the Foundational
Setup steps described in this plugin's design documents to be completed (connector installation,
workspace/team scoping, test scopes) before first live use.

Items still open before this plugin is fully live:
- **The shipped host profile and versioned configuration still ship as schemas with safe
  defaults, unconfigured, by design.** `host-profile.json` and `versioned-configuration.json` at
  the plugin root always default every operation to `unconfigured`/`null` — a real installation
  activates them via its own gitignored `.claude/workmanagement-kit.local.json`, never by editing
  the shipped files. This repository's own installation completed that activation live during
  Foundational Setup (`.draft/prompts/workmanagement-kit/_done/foundation-setup-wave1.md`): all
  four `notion.read`/`notion.write`/`linear.read`/`linear.write` operations are `verified` in this
  repo's own local override, with real resolved Notion workspace/database IDs and a real Linear
  organization/team ID. The transition contract and disposition record (both documented in
  `FOUNDATION_CONTRACTS.md`) are per-record write shapes, not standalone files — they became live
  the same moment the host profile did, since every write they describe already goes through that
  same sanctioning check.
  `plugin-integration-intake`'s own JSON Schema
  (`skills/plugin-integration-intake/assets/intake-payload.schema.json`, distinct from these four
  contracts) exists and defines the envelope's constraints, but nothing in this
  plugin currently invokes it programmatically — no script, hook, or MCP tool loads it at
  runtime yet. Until such an invocation exists, envelope validation happens only through
  `plugin-integration-intake`'s own step 2 procedure (the model reasoning through the schema's
  rules directly) or an ad-hoc check like `jsonschema` run by hand; see `intake-payload-schema.md`
  for what the schema defines and deliberately does not validate.
- **The Codex bridge-caller script (`scripts/bridge_caller.py`) that dispatches
  `work-transition-reviewer`/`work-intake-classifier` live is built and has run live, for real,
  against both agents** — see each agent's own body for its exact invocation. Known reliability
  caveat: on Windows, `codex exec --sandbox read-only` (what `codex-review-bridge` always uses) is
  intermittently flaky — one real dispatch during this script's own validation returned a
  `Windows error 1920` filesystem-access failure that a retry of the identical call did not
  reproduce. The script surfaces this as `bridge-invoke.mjs`'s own typed failure rather than
  silently skipping the review; a caller invoking it on Windows should be prepared to retry once
  before treating a failure as final. `linear-work-management`'s own SKILL.md separately documents
  a **connector-coverage gap**, found while wiring this script: the real Linear connector exposes
  Issue/Project/Milestone as real entities but has no `get_goal`/`save_goal` or
  `get_roadmap`/`save_roadmap` tool — Goal and Roadmap (two of `linear-entity-fields.md`'s five
  entity types) have no direct write path today.
- `plugin-integration-intake`'s trust-boundary gate had its first `security-reviewer` pass during
  this plugin's `plugin-lifecycle-downstream` QA run (2026-08-30); the Critical and Major findings
  from that pass are fixed in that skill's own file. Re-run the pass again before this gate is
  wired to a live connector.
