# Dependencies on workmanagement-kit (Wave 3a)

"Wave 3a" is the planned `workmanagement-kit` work that extends `plugin-integration-intake`. workledger-kit
needs capabilities that intake does not have today. Until they ship, every skill that would write runs in
**plan mode**: it collects, annotates, plans and writes its files into the local working folder, and stops
before submitting.

## Capability flags

`intake_capabilities` in `workledger-kit.settings.json` holds four booleans, all `false` by default. A local
override must list **all four** keys (the loader validates the exact key set and replaces the whole object).

| Key | Meaning when `true` | Needed by |
|---|---|---|
| `batch` | Intake accepts a batch with one approval per source batch, and Report page-content blocks | Submitting any source batch or any report |
| `query` | Intake can read existing Linear issues and the roadmap | Dedup against Linear; the roadmap report; onboarding verification |
| `update` | Intake can update an existing issue | Reserved: no skill step reads it yet (drift correction and status writes are future work) |
| `classify` | A caller can request classification of ambiguous source text | Reserved: no skill step reads it yet (ambiguous follow-ups and inferred PR links stay "needs your decision") |

A person sets a flag in `.claude/workledger-kit.local.json` once the matching Wave 3a work has shipped. The
config loader refuses `intake_capabilities` from a **tracked** copy of that file (decided case-insensitively,
and also when the file sits under a submodule or another work tree), because flipping a flag enables writes
and a tracked file could have been committed by anyone with repo write access.

What that check proves is only that the local file is **untracked**. It does not prove who wrote it:
`onboarding-repositories` writes it after approval, but the person, or any approved or auto-approved `Write`,
can change it. For that reason a skill that is about to submit re-runs `wlgr_config.py` and stops if `repos`
or `intake_capabilities` differ from the values it showed at the start. Intake's own live approval remains
the real gate on every write.

The shipped defaults list no repository (`repos` is empty) and every capability flag is off, so a project that
installs this plugin collects nothing until it onboards its own repository.

A single Report is gated on `batch` deliberately, not because intake lacks single-record support: a full
report cannot be expressed as `title`, `summary` and `body` within 2,000 characters per value, and the
page-content support that fixes that ships with the batch work (this rationale lives here only; the skills and
layout files point to it).

## Behavior by flag

| Situation | Behavior |
|---|---|
| `batch` is `false` | Plan mode only: write the plan, payload and report files; do not submit. Say plainly that submission waits for intake's batch and page-content support. |
| `query` is `false` | Dedup runs only within the collected candidate set. State that Linear was not consulted, so the plan may re-propose items that already exist. Never submit in this state. The roadmap report stops. Onboarding reports Linear-side steps as attested, not verified. |
| `classify` is `false` | Ambiguous candidates are marked "needs your decision" with their evidence in the preview. Nothing is classified automatically. |
| `update` is `false` | Candidate-matches and drift are reported only; no correction is proposed as a write. |

## Wave 3a work this plugin relies on

Recorded here so Wave 3a's own plan can be checked against it. All of it sits behind intake's existing
`security-reviewer` gate.

- Batch submission with one approval per source batch (hash-bound to the previewed set, chunked and
  resumable) instead of one approval per record.
- Report **page-content blocks**: a way to submit a report longer than 2,000 characters (intake accepts only
  `title`, `summary` and `body` today and rejects other fields).
- Query and update operations on Linear issues, including the roadmap (Initiatives, Projects, Milestones),
  plus a way to attach a PR URL as a native link and to set the due date to the completed date.
- A caller-reachable classification path, so ambiguous follow-ups and inferred PR links can reach the kit's
  Codex classifier (`work-intake-classifier`). The plugin cannot call that classifier directly.
- Multi-team configuration in the kit: today its configuration holds one repository and one team, so intake
  cannot resolve `owner/repo` to a team or reject an unknown repository. Until then a payload's
  `linear_target` gets an ambiguous-target hand-off.

## Not collected in v1

- **Unresolved review threads.** Resolution state exists only in GraphQL, which `gh` sends as a POST; this
  plugin is strictly read-only toward GitHub and reads through a GET-only wrapper. A review comment can
  still appear as a follow-up if a PR body names it.
- **Label creation for a new repository.** Intake has no label operation, so `onboarding-repositories` emits
  a label plan for a person to apply through `linear-work-management`.

## Residual risk: skills cannot restrict other tools

A skill's `allowed-tools` only **pre-approves** the tools it lists; it does not remove any other tool from
the session. The rule that this plugin never calls a Linear or Notion connector and never writes to GitHub is
therefore a procedure, backed by the scripts (GET-only wrapper, file-name-only CLI), not a mechanical block.
If the session has Linear or Notion write tools or `gh` write commands auto-allowed, injected text could in
principle steer the model to call them directly. Mitigations in place: collected text is treated as data,
no skill grants those tools, and intake re-asks approval. A `disallowed-tools` entry or a `PreToolUse` guard
would make it mechanical; neither has been added because the field's matching rules are undocumented and a
turn-scoped denial might also block intake's own calls. That is a recorded follow-up, not a solved problem.

## Write is pre-approved in three skills

`syncing-open-items`, `reporting-roadmap` and `onboarding-repositories` list `Write` in `allowed-tools`
(plugin-rulebook R6 requires a tool a skill's steps use to be listed; the plugin owner chose compliance over
keeping those writes prompting). The grant has no path scope. A prompt-injected run could therefore write
any file, including `.claude/workledger-kit.local.json`, without a prompt, and that file is the one the
loader trusts for `repos`, `digest` and `intake_capabilities`. The mitigations in place are limited:
`onboarding-repositories` is the only skill that is told to write it (after approval), every submitting skill
re-runs `wlgr_config.py` just before submitting and stops if `repos` or `intake_capabilities` changed since it
started, and intake's own live approval remains the gate on every write to Linear or Notion.

**Recorded follow-up (a further Linear issue, requested 2026-10-07):** protect the trusted local config with a
hook, for example a `PreToolUse` guard that denies `Write` and `Edit` to `.claude/workledger-kit.local.json`
unless the call comes from `onboarding-repositories` after its approval step. It is a new security gate, so it
needs its own `security-reviewer` pass before it ships. Until then this risk is accepted, not solved.
