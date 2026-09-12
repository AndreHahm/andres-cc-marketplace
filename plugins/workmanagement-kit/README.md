# workmanagement-kit

The sole Notion/Linear access point for this repository, per `FOUNDATION_CONTRACTS.md`'s Authority
Model: Notion owns knowledge and intent (Ideas, Decisions, proposed Goals, Notes, Research,
Reports, and Outcome/Learning records), Linear owns accepted strategy and execution (Goals,
Roadmaps, Projects, Milestones, Issues), and GitHub owns repository facts. Claude Code is the only
agent that mutates either Notion or Linear; Codex is a secondary, read-only reviewer.

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
  Codex CLI use) is built and live; the live in-session path (via this plugin's own
  `scripts/bridge_caller.py`, dispatching through `codex-kit`'s `codex-review-bridge`) is built and
  confirmed working in this monorepo's own checkout, but currently only in that layout — see Status
  for the open marketplace-install limitation.

Wave 2 additively bridges accepted Linear work to Git/GitHub implementation, orchestrating this
repository's own `git-kit` lifecycle skills rather than reimplementing any of them:

- **`repository-gates`** — discover, delegate, record, and invalidate this repository's actual
  Git/GitHub lifecycle gates and the repository-policy provider profile that maps governed
  operations to `git-kit`.
- **`linear-github-linking`** — record and reconcile stable reciprocal links among a Linear Issue
  and its GitHub branches, commits, and pull requests, with drift classification and bounded
  repair.
- **`work-to-development`** — validate an accepted Linear Issue's readiness and request governed
  branch/worktree creation through `git-kit:starting-work`.
- **`development-to-pr`** — supply Linear context and coordinate a governed commit, then either a
  new draft PR via `git-kit:create-pr` or a push to an already-existing PR's own branch via
  `git-kit:commit`'s own push.
- **`pr-to-linear`** — read a published PR's checks/reviews/threads, delegate the actual
  finding-triage/fix/reply/resolve cycle to `git-kit:handling-review-findings`, and write
  deliberate blocker summaries into Linear.
- **`merge-to-completion`** — coordinate governed merge readiness/execution through
  `git-kit:merge-pr`, then separately evaluate each Linear acceptance criterion before any
  closure decision — a merge alone never closes Linear work.
- **`linear-github-reconciliation`** — a broader drift sweep across Linear, Git, GitHub, and
  recorded evidence against the Authority Model, repairing only bounded fields.
- **`linear-github-lifecycle`** — composes `work-to-development`, `development-to-pr`,
  `pr-to-linear`, `merge-to-completion`, and Wave 1's `status-and-learning` end to end (plus
  `linear-github-linking` for evidence lookups and `linear-github-reconciliation` on demand),
  with resumable phase state. `repository-gates` is reached indirectly, through the delegated
  phase skills, not called by this skill directly.

This plugin depends on `codex-kit` for the live Codex review path and on `git-kit` for every
governed Git/GitHub operation Wave 2's skills delegate to.

## Installation

Install from this marketplace the same way as any other plugin in this repository (see the
repository's own installation instructions). `codex-kit` must also be installed for the live
Codex review path to function; without it (or on a Codex dispatch failure), `scripts/bridge_caller.py`
returns the bridge's own typed failure rather than silently skipping the review — see Status for
the script's current known reliability caveat on Windows. **The live Codex review path currently
only works when both plugins are installed as part of this monorepo's own checkout** —
`scripts/bridge_caller.py` resolves its own repo root and its `codex-kit` dependency by assuming a
shared monorepo layout, and returns a typed failure rather than dispatching when installed as two
independent marketplace plugins outside that layout (see Status). `git-kit` must be installed for any Wave 2
skill's governed Git/GitHub operations to resolve — without it, `repository-gates` fails closed with
a manual handoff rather than falling back to a raw `git`/`gh` command.

## Status

Both waves of this plugin's two-wave design are now built: Wave 1 (Notion/Linear foundation) and
Wave 2 (an additive Git/GitHub lifecycle bridge, orchestrating `git-kit`'s existing lifecycle rather
than reimplementing it). Live Notion/Linear mutation requires the Foundational Setup steps described
in this plugin's design documents to be completed (connector installation, workspace/team scoping,
test scopes) before first live use; Wave 2 additionally requires `repository_policy.provider_profile`
to be set to `git-kit` in `versioned-configuration.json`'s local override before any Wave 2 skill's
governed operations will resolve (see `repository-gates`'s own Failure and Resume section) — this
repository has not yet activated a local override for that field.

Items still open before Wave 2 is fully live:
- **The live Codex review path (`scripts/bridge_caller.py`) only works inside this monorepo's own
  checkout layout** — it cannot locate its own repo root or its `codex-kit` dependency when
  `workmanagement-kit` is installed standalone via the plugin marketplace mechanism into a
  consumer project. Tracked at
  `issues/2026-09-01-workmanagement-kit-bridge-caller-marketplace-install-path.md`. Doesn't block
  this repository's own live use (confirmed working end-to-end), but blocks the "install this
  plugin as usual" story for any installation outside this monorepo.
- **`versioned-configuration.json`'s schema-v2 `github`/`repository_policy` fields ship unconfigured
  by design**, same shippable-defaults-plus-local-override model every existing field already uses —
  an installation activates them via `.claude/workmanagement-kit.local.json`, never by editing the
  shipped file.
- **RESOLVED (2026-09-11):** all Wave 2 skills, plus `linear-work-management` and `work-linking` from
  Wave 1, now carry at least 3 real `skill-tester` Quick Workflow eval scenarios each (under
  `evals/<skill-name>/`), matching plugin-rulebook's `min_eval_scenarios` threshold — closed during
  this plugin's `plugin-lifecycle-downstream` QA run via 17 new scenarios and 34 real
  with_skill-vs-baseline comparison runs.
- **RESOLVED (2026-09-12):** `development-to-pr`'s existing-PR path now runs its own mandatory
  pre-push `cross-model-review` gate (step 2.5, scoped `BASE=HEAD` so it reviews only the pending
  uncommitted change, not the whole already-committed PR diff) before `git-kit:commit` is ever
  invoked — closed during a follow-up `plugin-lifecycle-downstream` QA pass, verified by a live
  Codex-dispatch `cross-model-review` run against the fix itself.
- **No `git-kit` skill currently owns marking a draft PR ready for review as a callable action** —
  `pr-to-linear`'s own "Marking ready" step is a disclosed manual handoff (the user runs `gh pr ready`
  themselves) rather than a delegated mutation. Tracked as a `git-kit`-level follow-up at
  [issue #318](https://github.com/AndreHahm/andres-cc-marketplace/issues/318).
- **`git-github-evidence` will hit the same real-connector custom-field limitation an already-tracked
  Wave 1 issue documents for `notion-link`/`disposition-history`/`open-item-source`/`transition-id`**
  (`issues/2026-08-31-workmanagement-kit-notion-linear-connector-field-limitations.md`) — the real
  Linear connector's `save_issue` exposes no generic custom-field mechanism. Resolve with the same
  workaround encoding (or a real custom field) that issue proposes, before writing `git-github-evidence`
  against a live connector.

Items still open from Wave 1:
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

## Contributing

See `CONTRIBUTING.md` for this plugin's preferred scripting language and change-proposal process.

## License

Licensed under Apache 2.0 — see `LICENSE`.
