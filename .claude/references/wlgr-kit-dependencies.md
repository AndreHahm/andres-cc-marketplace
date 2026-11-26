# Dependencies on workmanagement-kit (Wave 3a)

"Wave 3a" is the planned `workmanagement-kit` work that extends `plugin-integration-intake`. workledger-kit
needs these capabilities. Intake now has Issue batches, dedup-key queries, updates, `classify` and `owner/repo`
resolution; Report page-content blocks and roadmap reads are still missing. Every flag below ships `false`, and until
a person sets one, the skills it gates run in **plan mode**: they collect, annotate, plan and write their files into
the local working folder, and stop before submitting. This file is the canonical list of the intake capabilities
workledger-kit needs and of the flags that gate each one; other files point here instead of restating it.

## Capability flags

`intake_capabilities` in `workledger-kit.settings.json` holds four booleans, all `false` by default. A local
override must list **all four** keys (the loader validates the exact key set and replaces the whole object).

| Key | Meaning when `true` | Needed by |
|---|---|---|
| `batch` | Intake accepts a batch with one approval per source batch, and Report page-content blocks | Submitting any source batch or any report |
| `query` | Intake can read existing Linear issues and the roadmap | Dedup against Linear; the roadmap report; onboarding verification |
| `update` | Intake can update an existing issue | Reserved: no skill step reads it yet (drift correction and status writes are future work) |
| `classify` | A caller can request an advisory open-item classification of ambiguous source text (intake's `classify` operation) | Reserved: no skill step reads it yet (ambiguous follow-ups stay "needs your decision"; inferred PR links are not produced) |

A person sets a flag in `.claude/workledger-kit.local.json` only once everything in its "Meaning when `true`" cell has
shipped. `batch` and `query` therefore stay `false` for now: Report page-content blocks and roadmap reads are missing. The
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
  plus a way to attach a PR URL as a native link and to set the due date to the completed date (the link and the due date are available through an update).
- A caller-reachable classification path, so ambiguous follow-ups can reach the kit's Codex classifier
  (`work-intake-classifier`); the plugin cannot call that classifier directly. Intake's `classify` operation is
  that path: at most 50 items of 500 characters, one live approval per submission because the text goes to
  Codex, advisory results only. Inferred PR links are not part of it.
- Multi-team configuration in the kit: its `linear.repositories` configuration maps an `owner/repo` slug to a team
  through `linear-work-management`. A payload whose slug is not mapped gets a structured handoff.

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
no skill grants those tools, and intake re-asks approval. A `disallowed-tools` entry or a `PreToolUse` guard for connectors
would make it mechanical; neither has been added because the field's matching rules are undocumented and a
turn-scoped denial might also block intake's own calls. That is a recorded follow-up, not a solved problem.

## Write is pre-approved in three skills

`syncing-open-items`, `reporting-roadmap` and `onboarding-repositories` list `Write` in `allowed-tools`
(plugin-rulebook R6 requires a tool a skill's steps use to be listed; the plugin owner chose compliance over
keeping those writes prompting). The grant is a bare `Write` with no path scope. It could be scoped: an
`Edit(<glob>)` rule is the path-scoped form that also covers the `Write` tool, while a `Write(<glob>)` rule
is accepted but never matches (issue #587; checked live, Claude Code 2.1.302, Linux, headless run in default
permission mode). These skills are left unscoped because their write targets (a working directory chosen at
run time, a report path the person names) are not a fixed set; scoping them is a per-skill decision still
open under #591. In default permission mode (the only mode probed), a prompt-injected run could therefore
write a file outside `.claude/` without a prompt.
The same probe refused both `.claude/` paths it tried with the bare `Write` grant (`.claude/NOTES.md` and
`.claude/workledger-kit.local.json`) as sensitive-file writes, so `.claude/workledger-kit.local.json` was not writable without a decision
from the person in that run. That file is the one the loader trusts for `repos`, `digest` and
`intake_capabilities`, and the refusal depends on Claude Code's sensitive-file protection, not on this
plugin. The mitigations in place are limited:
`onboarding-repositories` is the only skill that is told to write it (after approval), every submitting skill
re-runs `wlgr_config.py` just before submitting and stops if `repos` or `intake_capabilities` changed since it
started, and intake's own live approval remains the gate on every write to Linear or Notion.

**Guard hook (2026-11-25).** `hooks/wlgr-guard-local-config.sh` is a plugin-level `PreToolUse` hook on `Write`,
`Edit` and `MultiEdit`. It prints one fixed `ask` when the call's path contains `workledger-kit.local.json` (any ASCII
letter case) or its usual Windows short-name stem, and nothing otherwise; when the input has no readable path, the
whole input is searched instead. It never allows, and it does not know which skill
is calling: a hook cannot see that, and a marker the model wrote itself would prove nothing, so the person's answer is
the control. `onboarding-repositories` therefore normally raises that prompt on its approved write too. It is a Bash
script, not Python like the rest of this plugin, on purpose: it runs no interpreter and opens no path from the
repository being edited.

Not covered, and accepted:

- Shell commands (`Bash`, PowerShell) can write the file without passing the hook.
- A symlink or hard link with another name, and a Unicode look-alike that a file system treats as the same name: the
  hook compares text only. The same goes for the hash-form short name Windows uses after several collisions.
- It is not documented that `ask` always prompts in `bypassPermissions` mode, or for a protected path in `auto` mode
  (where Claude Code's classifier may decide first). Neither was checked live.
- The hook fails open if it cannot start, times out, or cannot read its input (`cat` is run by absolute path, never found through `PATH`). `onError` is `warn`, as in this repository's other hooks, and
  `onFailure` (Claude Code's hooks reference) is unset, because `block` would stop every `Write` and `Edit` in the
  project when the hook is broken. Claude Code's own protection of `.claude/` remains.
- The hook is active in any project that installs this plugin.
