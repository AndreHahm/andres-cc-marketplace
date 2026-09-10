# Foundation Contracts

This plugin's skills share four contracts, referenced throughout as "the plugin's shared host
profile," "the plugin's shared transition contract," "the plugin's versioned configuration," and (for
`open-item-management` specifically) "the plugin's disposition record." This file is the single
canonical definition of all four — every skill citing one of them points here, rather than each
restating its own description (the exact drift risk R20 exists to catch).

## Host Profile (`host-profile.json`)

Maps a logical operation (`notion.read`, `notion.write`, `linear.read`, `linear.write`) to whether
it is currently sanctioned for use, and to what scope. **Tool presence in a session is never proof
of permission** — a skill's `allowed-tools` grant can name an MCP tool that exists, while the host
profile still says that operation is `unconfigured`. Every skill that reads or writes Notion/Linear
must check this file's `support_status`/`verified_at` fields for the specific operation before
calling the connector, even when the connector tool itself is callable.

Shipped with every operation defaulting to `unconfigured` — this is a schema-with-safe-defaults
file, not a functioning connector configuration. An installation makes it functional by overriding
fields via `.claude/workmanagement-kit.local.json` (gitignored, untracked; see Local Override
below) — never by editing `host-profile.json` directly, since that file is the plugin's own
shippable default and edits to it would be lost on plugin update and visible to every installation.

**Schema:**

```json
{
  "version": 1,
  "operations": {
    "notion.read":   {"support_status": "unconfigured", "verified_at": null, "connector": null, "workspace_id": null},
    "notion.write":  {"support_status": "unconfigured", "verified_at": null, "connector": null, "workspace_id": null},
    "linear.read":   {"support_status": "unconfigured", "verified_at": null, "connector": null, "organization_id": null, "team_ids": []},
    "linear.write":  {"support_status": "unconfigured", "verified_at": null, "connector": null, "organization_id": null, "team_ids": []}
  }
}
```

- `support_status` — one of `unconfigured` (default; not yet set up, no write may proceed),
  `verified` (an installer has confirmed the connector, scope, and identity for this operation),
  or `revoked` (was verified, access has since been withdrawn — treat identically to
  `unconfigured` for gating purposes, but preserve the distinction for audit history).
- `verified_at` — ISO-8601 UTC timestamp of the last verification, or `null` if never verified.
- `connector` — the installed MCP connector's own identifier (e.g. `claude_ai_Notion`), or `null`.
- `workspace_id` (Notion) / `organization_id`+`team_ids` (Linear) — the approved scope. A skill
  must never act outside the scope named here, even when the connector tool itself would allow it.

## Versioned Configuration (`versioned-configuration.json`)

Stores the stable IDs an installation resolves once, during Bootstrap (see
`notion-knowledge-management/SKILL.md`'s Bootstrap section), rather than re-resolving them by
display name on every write — display names are not unique and must never be used as a stored
reference (see `linear-entity-fields.md`'s Cross-Entity Rules for the same rule on the Linear side).

Shipped with every field `null`/empty — same shippable-defaults-plus-local-override model as the
host profile. An installation's real stable IDs belong in `.claude/workmanagement-kit.local.json`,
never committed to `versioned-configuration.json` itself (a workspace/team ID is installation-
specific, not a fact about the plugin).

**Schema:**

```json
{
  "version": 1,
  "notion": {
    "production_workspace_id": null,
    "test_workspace_id": null,
    "databases": {
      "test": {},
      "prod": {}
    }
  },
  "linear": {
    "organization_id": null,
    "production_team_id": null,
    "test_team_id": null
  }
}
```

- `notion.databases` — an object with exactly two keys, `test` and `prod`, each itself a map from
  Notion record type (`idea`, `decision`, `proposed-goal`, `note`, `research`, `report`,
  `outcome-learning`) to that type's resolved database ID **for that environment**, populated
  incrementally as Bootstrap resolves each type — never required to be fully populated at once, and
  the two environments' maps are populated independently (resolving `test.idea` implies nothing
  about whether `prod.idea` is resolved yet). Both environments need their own resolved database ID
  per record type even when `production_workspace_id` and `test_workspace_id` happen to be the same
  physical Notion workspace (isolation then comes from separate databases within that shared
  workspace, not from separate workspace IDs) — a single-level flat map cannot represent both
  environments' database IDs at once, since a record-type key alone doesn't say which environment's
  database it resolves to. **Naming note:** `databases`' `test`/`prod` keys and the sibling
  `test_workspace_id`/`production_workspace_id` fields name two independent concepts (which database
  a record type resolves to, vs. which Notion workspace scope is approved) that happen to share the
  same environment vocabulary (`test`/`prod` vs. `test_workspace_id`/`production_workspace_id`) —
  any future resolver code reading both must not assume a shared literal string; translate
  `production_workspace_id`'s `production` to `databases`' `prod` key explicitly rather than deriving
  one name from the other.
- `test_workspace_id` / `test_team_id` — the isolated test locations Bootstrap also resolves,
  per its own "resolve the production and an isolated test location" instruction.

## Local Override (`.claude/workmanagement-kit.local.json`)

Gitignored, untracked, created by an installer during Foundational Setup — not shipped with this
plugin and not created by this repository's own build. Merges over both files above by top-level
key (`host_profile`, `versioned_configuration`), the same override model `.claude/git-kit.local.json`
already uses for `git-kit`'s own settings — **the merge is deep at the operation level within
`host_profile.operations`, never a wholesale replacement of the `operations` object**: an override
that sets only `notion.read` must not cause `notion.write`/`linear.read`/`linear.write` to
disappear from the merged result — each is merged independently, key by key, and any operation the
override doesn't mention keeps the shipped file's own `unconfigured` default untouched. The same
per-key merge applies to `versioned_configuration`'s nested objects (`notion.databases`, etc.).

```json
{
  "host_profile": { "operations": { "notion.read": {"support_status": "verified", "...": "..."} } },
  "versioned_configuration": { "notion": {"production_workspace_id": "...", "...": "..."} }
}
```

**A tracked copy of this file must be treated with the same trust-boundary discipline
`git-kit.local.json`'s own security-relevant fields already require, not exempted from it.** This
file's `support_status`/`workspace_id`/`organization_id`/`team_ids`/`connector` fields are exactly
the kind of trust-relevant claim that pattern exists for: `support_status: "verified"` is the
precondition every skill's "Resolving the connector" step checks before it will even attempt a
connector call at all (see e.g. `notion-knowledge-management/SKILL.md`'s own section) — a tracked
copy committed by anyone with repo write access (this file is gitignored by convention, but a
`git add -f` still tracks it) could falsely assert `verified` status and a scope
(`workspace_id`/`organization_id`/`team_ids`) an attacker controls, for any unwitting user who later
checks out that branch. The per-write `AskUserQuestion` approval gate is a separate, hardcoded check
in each skill and still fires regardless — this file's claims alone can never cause a write to
happen with no human in the loop — but a forged `verified`/scope claim still reaches that approval
prompt as if it were legitimate, which is a real trust-boundary gap, not a merely cosmetic one.
Before honoring this file's `host_profile`/`versioned_configuration` overrides, resolve whether it
is genuinely untracked the same way `commit`'s own trust check does: a repo-root-anchored,
glob-disabled pathspec (`git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json"`),
branching on the exact outcome — confirmed-untracked (exit 1, "did not match any file(s)") is the
only case that may honor this file's overrides; tracked (exit 0) or unverifiable (any other outcome)
must fall back to the shipped `unconfigured` defaults, the same fail-closed discipline
`git-kit`'s own `commit` skill uses for its trust check, never a two-way pass/fail collapse.

**Redact real identifiers before persisting live-run output to a tracked location.** Once this
file is activated for a real installation, its resolved workspace/organization/team/database IDs
and any workspace-specific URL (e.g. `linear.app/<workspace-slug>/...`) are real, live-account
identifiers — not credentials, but real enough to identify and locate the account. Any eval output,
`.claude/output/` artifact, or other tracked file that narrates a live-connector run must have these
values replaced with an obvious placeholder (e.g. `<redacted-team-id>`, `example-workspace`) before
being committed — never persisted verbatim just because the run happened to be real. Found live: a
prior session's `evals/linear-work-management/`, `evals/idea-to-implementation/`, and
`evals/work-linking/` output files persisted this repo's own real Linear team ID, workspace slug,
and account display name verbatim; redacted during `finalize-setup-connectivity.md`'s own security
review (GitHub issue #251).

## Transition Contract

The shape every skill's "record the resulting transition" step must produce for **a single write to
a single record** — embedded as that record's own `transition-id`-tagged properties (see each
Notion/Linear record type's shared-field list); this is not a separate log file, the evidence lives
inline on the record itself. This contract represents exactly one write's own evidence and nothing
more: it has no field for a cross-system link pair (see the already-shipped `notion-link`/
`linear-link` entity fields, used directly by `work-linking`, for that) and no field for a batch of
independent per-item outcomes against one source record (see Disposition Record below, used by
`open-item-management`, for that) — forcing either shape into this schema's single-valued fields is
exactly the gap GitHub issue #254 identified; both are handled by their own dedicated mechanism
instead.

**Schema:**

```json
{
  "transition_id": "string, a stable unique ID for this transition",
  "operation_id": "string, the connector call's own operation/request ID, if the connector provides one, else null",
  "affected_record": {"system": "notion | linear | github", "stable_id": "string"},
  "source_plugin": "string, the plugin that caused this transition, or 'workmanagement-kit' for a direct user request",
  "verification_evidence": "string, a description of the read-back that confirmed the PRIOR write to this record succeeded, or null if this plugin made no earlier write of its own to this record (e.g. adopting an already-existing record) — see 'Recording verification_evidence' below, including why a newly-created record's first transition-tagged write is NOT this null case",
  "recorded_at": "ISO-8601 UTC timestamp"
}
```

- `transition_id` — generated fresh per transition, never reused; a Decision Supersede (which
  produces two writes — see `notion-knowledge-management/SKILL.md`'s Decision State Machine) gets
  two distinct `transition_id`s, one per write, linked via each record's own `related-record` field.
- `source_plugin` — for a submission routed through `plugin-integration-intake`, this is the
  caller's claimed `source_plugin` value (caller-asserted, not host-attested — see that skill's own
  Trust Model section); for a direct user request, this is always `"workmanagement-kit"` itself.
- `verification_evidence` — a human-readable description (e.g. `"read back via linear.read,
  confirmed status=Done"`), not a raw connector response dump. Describes the read-back of the
  record's *previous* write, not this one — see below for why.

### Recording verification_evidence (the next-write convention)

`verification_evidence` can only be known after its own write completes (the read-back that
confirms it), but "the evidence lives inline on the record itself" means it must be embedded in a
write, not floated in a separate log — a write can't embed evidence of its own success before it has
happened. This plugin resolves that causality gap with a **next-write convention**: when a skill
writes to a record for the Nth time, that write's own `transition_id`/`operation_id`/
`affected_record`/`source_plugin` describe write N itself, while the `verification_evidence` field
in that *same* write instead carries the read-back that already confirmed write N-1 succeeded
(known before write N started, since the read-back happens immediately after N-1 completes and
before N is even drafted). Write N's own verification_evidence is deferred the same way, to
whatever write N+1 does.

**Terminal-write exception:** if a record's write N is expected to be its last write (no write N+1
is planned), write N's own verification_evidence has no future write to attach to. In that case, the
skill performs one additional metadata-only write to the same record whose sole purpose is recording
write N's verification_evidence. This metadata write is exempt from needing its own read-back
recorded via a further write — doing so would recurse indefinitely — since it changes nothing but
the evidence field itself; a plain read confirming the metadata write landed is enough. Every skill
citing this contract's Read-Back and Transitions convention inherits this exception without needing
to restate it. **This metadata write needs no fresh approval of its own by default** — it changes
only the evidence field, never the record's actual content, and the write it confirms was already
approved (or needed none, for a read-derived transition); a skill's own Confirmation and Safety
section may say so explicitly, but the exemption holds either way. **This default yields to a
consuming skill's own stricter, unconditional approval policy** — `plugin-integration-intake`'s own
"every actual write... no exception for a 'low-risk' or 'read-only-looking' submission" rule is
absolute by that skill's own design and is never relaxed by this exemption: a terminal metadata
write recording the evidence of an intake-routed transition still goes through
`plugin-integration-intake`'s live approval gate like any other write it causes, exactly as that
skill's own Confirmation and Safety section already requires.

**Creation-write exception:** the next-write convention above assumes `affected_record.stable_id`
is already known before the write starts — true for a write to an *existing* record, but not for
the write that *creates* one: its stable ID is assigned by the connector's create response and does
not exist before that response returns, so it cannot be embedded in that same create write's own
properties. Since the Transition Contract's fields are embedded together as one unit (this file's
own intro line, "the record's own `transition-id`-tagged properties"), a create write can't
partially embed the three fields it does already know (`transition_id`, generated client-side;
`source_plugin`, always known ahead of time; `operation_id`, if the connector supplies one as a
client-side request ID) while leaving `affected_record` for later — the whole transition is
deferred together, and the create write itself carries none of the Transition Contract's fields at
all.

Immediately after the create response returns, read the new record back to confirm it — this
read-back **is** the create's own `verification_evidence`, produced by the ordinary next-write
convention exactly as it would be for any other write; it is not `null`, since the create is a real
preceding write with real evidence, not an absence of one. **The skill's very next write to that
record is now an ordinary write to an existing record — it embeds its own `transition_id`/
`operation_id`/`affected_record`/`source_plugin`, describing itself, exactly like any other write
under the ordinary next-write convention** (never the create's own transition_id — the create's
identity as a transition, beyond the read-back evidence it produced, is not separately retained;
this is the same single-snapshot limitation already disclosed for every other write, tracked as
issue #260, not a new gap this exception introduces). That write's `verification_evidence` carries
the create's own read-back, per the ordinary next-write convention.

**This matters when the record's next write is materially significant in its own right** — e.g.
`idea-to-implementation`'s reciprocal-link write, not a bookkeeping-only follow-up: that write's own
transition (identifying *that* write) is what gets embedded, never the create's. If that same write
also turns out to be the record's terminal write (nothing else planned), the terminal-write
exception's own exemption applies to it as usual — it needs no further write of its own to record
its own read-back, a plain confirming read is enough — but its `verification_evidence` field still
correctly carries the *create's* evidence (per the paragraph above), not its own; its own read-back
is what the exemption excuses it from needing to record further, exactly as the terminal-write
exception already describes for any other write.

## Disposition Record (`disposition-history`)

A separate, repeatable mechanism for the case the Transition Contract above cannot represent: one
pass producing more than one independent outcome against a single source record (e.g.
`open-item-management` dispositioning every open item from one Report/Decision/Issue in a single
pass). The Transition Contract's fields are single-valued per write — a second item's outcome would
simply overwrite the first's rather than accumulate — so this uses its own array-valued property
instead.

Stored as an array-valued `disposition-history` property directly on the source record (see the
`disposition-history` row in `notion-record-types.md`'s Report/Decision tables and
`linear-entity-fields.md`'s Issue table). Appended to on every dispositioning pass, never
overwritten or replaced wholesale — a record accumulates one entry per item across its lifetime,
potentially from more than one pass over time.

**Schema (one array entry per item):**

```json
{
  "item_id": "string, an identifier for this open item that stays stable ACROSS passes over the same source (e.g. a hash of the item's own stated content) — not just within the pass that produced it",
  "disposition": "resolved | retained-knowledge | decision-needed | actionable-work",
  "note": "string, human-readable reason/context for this disposition",
  "linked_record": "string, stable ID of the Linear follow-up created for this item, or null (set only when disposition is actionable-work)",
  "transition_id": "string, the Transition Contract transition_id of the write that appended this entry",
  "recorded_at": "ISO-8601 UTC timestamp"
}
```

- `item_id` must be stable across passes, not just within the one that produced it — derive it
  **only from the item's own stated text**, never from surrounding section/context (context can
  change between passes for reasons unrelated to this item — a heading edit, a neighboring item
  added or removed — which would silently change the derived ID and break re-run matching even
  though the item itself didn't change) and never from a positional index, which has the same
  instability. A later re-run over the same source needs `item_id` to recognize an item it already
  dispositioned, which only the item's own unchanged text can reliably support. This does allow a
  genuine collision — two different items in the same source whose stated text happens to be
  byte-identical — but that's the correct trade-off: stability across passes is the property this
  field exists for; collision is the rarer failure mode. When it happens, this is a structured
  handoff: surface the ambiguity to the user rather than silently merging the items or arbitrarily
  assigning the collision to one.
- `disposition` uses this hyphenated form; a consuming skill's own prose (e.g.
  `open-item-management`'s "retained knowledge", "Decision needed") maps directly to it — same four
  outcomes, just written for readability in prose versus this schema.
- **Reconsidering an already-dispositioned item** (a consuming skill's own flow may let the user
  explicitly ask to revisit one) appends a **new** entry with the same `item_id`, never an edit to
  the existing one — `disposition-history` stays append-only either way. The most recent entry for a
  given `item_id` is that item's current, authoritative disposition; an earlier entry for the same
  `item_id` is retained as history, not superseded in place. A consuming skill's own "does this item
  already have a recorded disposition" check must compare against the *most recent* entry for that
  `item_id`, not merely "any" entry, since a reconsidered item can have more than one.
- The write that appends one or more Disposition Record entries is itself an ordinary single write
  against the source record — it still gets its own ordinary Transition Contract entry
  (`affected_record` = the source record), per the next-write convention above. Each entry's own
  `transition_id` links back to that write's `transition_id`; it is not a transition of its own.
- Approval for the write that appends these entries is owned by the consuming skill (e.g.
  `open-item-management`'s own second, separate approval gate) — this contract defines the stored
  shape only, not the approval requirement.

**Companion field — `open-item-source` (on the follow-up Issue, not the source record):** a
Disposition Record entry's `linked_record` lives on the *source* record and is only set once the
full disposition write above completes — if that write is declined or fails after a follow-up
Issue was already created, the Issue itself would otherwise carry no persisted link back to its
source at all, with no way to repair it (Issue supports no delete operation). `open-item-source`
closes that gap: a lightweight `{"system": "notion | linear", "stable_id": "string", "item_id":
"string"}` reference set directly on the Issue as part of its own creation write (see
`linear-entity-fields.md`'s Issue table), independent of whether the full Disposition Record write
ever happens. `stable_id` identifies the source *record*; `item_id` identifies the specific open
item within it, using the identical value the Disposition Record entry for that item will use —
without it, a source with more than one actionable item would produce several follow-up Issues that
all carry the same `stable_id` and can't be told apart when recovering from a partial failure. It
needs no approval beyond whatever already gates the Issue's own creation — it is part of that same
write, not a separate one.

## Git/GitHub Evidence Record (`git-github-evidence`)

A separate, repeatable mechanism for Git/GitHub-specific evidence the base Transition Contract cannot
represent (repository identity, branch, multiple commits, PR identity, multiple gate results — all
single-valued fields in the base contract would only ever hold the latest one). Same shape of extension
Disposition Record already is for `open-item-management`'s multi-item case. Added by Wave 2
(`workmanagement-kit`'s Git/GitHub lifecycle bridge); the background Wave 2 design documents originally
described this as a `type` field added directly to the base Transition Contract, but the base contract
has no such field and adding one would have repeated exactly the single-valued-fields limitation
Disposition Record already exists to avoid — this record follows that same precedent instead.

Stored as an array-valued `git-github-evidence` property directly on the Linear Issue record (see
`linear-work-management/references/linear-entity-fields.md`'s Issue table). Appended to on every stage
transition, never overwritten — matches Disposition Record's append-only, superseded-not-deleted
convention.

**Schema (one array entry per stage transition):**

```json
{
  "evidence_id": "string, a stable unique ID for this evidence entry, never reused",
  "repository": "string, canonical repo slug, e.g. 'owner/repo'",
  "stage": "work-started | commit-linked | ci-gates-passed | pr-published | pr-ready | pr-merged | work-reopened",
  "branch": "string, or null until a branch exists",
  "base_branch": "string, or null",
  "commits": [ {"sha": "string", "recorded_at": "ISO-8601 UTC timestamp"} ],
  "pull_request": {"number": "integer", "url": "string", "state": "draft | open | merged | closed"} | null,
  "merge_commit_sha": "string, the actual merge SHA read back from GitHub for a pr-merged entry (may differ from any sha in commits[] — a squash/rebase merge produces a new commit not on the PR branch's own history), or null for every other stage",
  "gates": [ {"name": "string", "owner": "string", "result": "pass | fail | pending | bypassed", "sha": "string", "recorded_at": "ISO-8601 UTC timestamp"} ],
  "provider": "string, the git-kit skill that performed the underlying operation (e.g. 'git-kit:starting-work') for a stage a git-kit skill actually performed; 'workmanagement-kit:<skill>' for work-reopened, which has no git-kit operation of its own (e.g. 'workmanagement-kit:merge-to-completion'); or 'manual (<real command>, per <workmanagement-kit skill>'s disclosed handoff)' for a stage reached through a disclosed manual handoff because no git-kit skill owns that action yet (e.g. 'manual (gh pr ready, per pr-to-linear's disclosed handoff)') — never a fabricated git-kit attribution for an operation git-kit didn't actually perform",
  "policy_profile": "string, the repository-policy profile name this evidence was resolved under",
  "supersedes": "string, evidence_id of an earlier entry this one invalidates (e.g. a force-push changing a recorded SHA for the same branch/PR), or null",
  "transition_id": "string, the base Transition Contract transition_id of the write that appended this entry",
  "recorded_at": "ISO-8601 UTC timestamp"
}
```

- `stage` distinguishes each lifecycle checkpoint Wave 2 records.
- `pr-merged` and this plugin's Linear workflow-status closure (informally "`work-closed`") remain
  distinct: `pr-merged` is one array entry's `stage` value; the Linear Issue's own workflow status
  changing to Done/Closed is a separate, ordinary Linear write through `linear-work-management`, recorded
  via the **base** Transition Contract as always — never inferred from a `pr-merged` entry alone.
- Multiple commits/PRs per Issue are modeled by repeated array entries sharing the same `repository`, not
  a nested collection.
- `supersedes` implements supersede-without-delete, matching Disposition Record's own most-recent-wins
  convention exactly (not just "the same shape of extension" — the same resolution rule): a force-push
  or base change appends a **new** entry whose own `supersedes` field names the earlier entry's
  `evidence_id`. The pointer lives only on the new entry — the old entry is never touched, so "never
  overwritten"/"never edited in place" above holds literally, not just in spirit. A consuming skill's
  "is this evidence still current for this branch/PR" check must follow the same most-recent-entry-wins
  rule `disposition-history`'s own reconsideration note (above) already establishes for `item_id` — never
  look for a back-reference on the old entry, since none is ever written there.
- The write that appends a `git-github-evidence` entry is itself an ordinary single write against the
  Linear Issue — it still gets its own ordinary base Transition Contract entry (`affected_record` = the
  Issue), per the existing next-write convention. Each entry's own `transition_id` links back to that
  write's `transition_id`; it is not a transition of its own (identical relationship to how Disposition
  Record entries link back to their own appending write).
- **`affected_record.system` extension:** the base Transition Contract's `affected_record.system` enum
  (previously `"notion" | "linear"`) is extended to `"notion" | "linear" | "github"` — used when a
  transition's own `affected_record` is a GitHub artifact directly (rare; most Wave 2 writes affect the
  Linear Issue and carry `git-github-evidence` as a sub-property, not a separate GitHub-system write).

## Repository Policy Profile

Added by Wave 2. `repository_policy.provider_profile` (in `versioned-configuration.json`, schema v2)
names a profile mapping each governed Git/GitHub logical operation to its required provider. For this
repository, the profile is fixed — `git-kit` for every governed operation:

| Logical operation | Required provider |
|---|---|
| Create branch/worktree | `git-kit:starting-work` |
| Commit | `git-kit:commit` |
| Create a new PR | `git-kit:create-pr` |
| Push new commits to an already-existing PR's branch | `git-kit:commit` (its own push step — no `git-kit` skill owns a distinct "update an existing PR" mutation; see `development-to-pr`'s own Gotchas) |
| Mark a PR ready for review | Manual handoff — no `git-kit` skill currently owns this action (see `pr-to-linear`'s own disclosed gap and the `provider` schema note below) |
| Review/comment/link an issue at creation | `git-kit:collaborating-on-a-pr` |
| Merge | `git-kit:merge-pr` |
| Post-merge sync/cleanup | `git-kit:finishing-work` |

A profile with a missing/unconfigured provider for a governed operation fails closed — every Wave 2
skill stops with a manual handoff rather than falling back to a raw `git`/`gh` command.

## Change Log

- 2026-09-10 — Fixed an eleventh and twelfth `cross-model-review` finding, and disclosed a
  thirteenth as a known gap rather than a workaround. The Git/GitHub Evidence Record schema had no
  field for a merge's own SHA — `merge-to-completion` needed to record it and `status-and-learning`
  needed to read it, but the only array field (`commits[]`) holds a PR branch's own pre-merge
  commits, not the merge result (a squash/rebase merge produces a SHA that was never on that branch).
  Added a dedicated `merge_commit_sha` field. Separately, `repository-gates`'s own step 3 restated
  the Repository Policy Profile table as an inline paraphrase that had already drifted out of sync
  with the canonical table (still describing "publish → create-pr/collaborating-on-a-pr" after an
  earlier fix split that into three distinct operations) — now points at the canonical table directly
  instead of repeating a summary that can drift again. Disclosed, not fixed: `development-to-pr`'s
  existing-PR path pushes via `git-kit:commit`'s own step 16, which has no equivalent to
  `git-kit:create-pr`'s own mandatory pre-push `cross-model-review` gate — closing this properly needs
  a `git-kit`-level "commit, review, then push" capability that doesn't exist yet, out of scope for a
  Wave 2 fix; stated plainly in that skill's own Gotchas and the plugin's README rather than silently
  left uncovered.
- 2026-09-10 — Fixed a ninth and tenth `cross-model-review` finding, both tool-grant-vs-claimed-
  capability gaps in Wave 2's newer skills. `pr-to-linear` claimed to read "unresolved threads" via
  `gh pr view`, but that command's own JSON field list has no thread-resolution field (only GraphQL's
  `reviewThreads.isResolved` exposes it) and this skill holds no `gh api graphql` grant — corrected to
  rely entirely on `handling-review-findings`'s own fixed/filed/declined report (that skill does hold
  the GraphQL grant) as the sole source of truth for thread state, never independently re-derived.
  `repository-gates`'s own Invalidating Prior Evidence section compared a recorded gate SHA against
  "current HEAD" with no tool grant capable of determining that value itself — clarified that both
  SHAs being compared are always supplied by the calling skill from its own fresh read-back, matching
  this skill's own stated "discovery and delegation only" design rather than claiming an
  independent-determination capability it never had.
- 2026-09-10 — Fixed a fifth and sixth `cross-model-review` finding, both in Wave 2's newer skills:
  `repository-gates` documented running the exact `git ls-files` trust-boundary check this section
  requires before honoring `.claude/workmanagement-kit.local.json`, but its own `allowed-tools` never
  actually granted `Bash(git ls-files:*)` — a fail-closed check with no way to execute it, unlike
  Wave 1's `linear-work-management`/`notion-knowledge-management`, which already carry this grant for
  the identical check; added the missing grant and spelled out the exact command in the skill's own
  step 1. Separately, `development-to-pr`'s existing-PR branch treated `Adoptable` the same as
  `Exact` (already-confirmed) for deciding whether to push to that branch, but
  `linear-github-linking`'s own classification table requires an explicit `AskUserQuestion` identity
  confirmation before treating an `Adoptable` candidate as adopted — added that confirmation as its
  own step, before the commit-time branch decision.
- 2026-09-10 — Fixed a seventh and eighth `cross-model-review` finding. The Repository Policy Profile
  table's "Push/create PR" row only ever named `git-kit:create-pr`/`git-kit:collaborating-on-a-pr` as
  valid providers — never updated when `development-to-pr`'s existing-PR path (an earlier fix this
  same day) started using `git-kit:commit`'s own push instead, since neither of the table's two named
  skills actually owns that operation. Split the row into three accurately-scoped operations (create a
  new PR, push to an already-existing PR's branch, mark a PR ready) each naming its real provider,
  including the disclosed no-provider-yet gap for "mark ready." Separately, `merge-to-completion`'s
  own readiness-check description listed "unresolved threads" alongside the actual blocking checks it
  delegates to `git-kit:merge-pr` — but `merge-pr` documents unresolved-thread counts as disclosed to
  the human merging, never a blocking gate; the wrapper's own wording overstated what its delegate
  actually enforces. Corrected to name the five real blocking checks and state the disclosed-not-
  blocking behavior explicitly, matching `merge-pr`'s own documented contract.
- 2026-09-10 — Fixed a fourth `cross-model-review` finding, a self-inflicted follow-on from the
  `pr-ready` structured-handoff fix below: once `pr-to-linear`'s ready-state mutation became a
  disclosed manual `gh pr ready` run by the user (no `git-kit` skill performs it), the resulting
  `pr-ready` evidence entry had no truthful value for the `provider` field, which still required
  "the git-kit skill" with only the `work-reopened` exception carved out. Generalized the `provider`
  schema note to a third form — `"manual (<real command>, per <skill>'s disclosed handoff)"` — for
  exactly this case, and updated `pr-to-linear`'s step 9 and `work-transition-reviewer`'s Provider
  check to use and recognize it. Also fixed a related gap in `development-to-pr`: its own gate
  read-back (step 12) had no schema-valid place to record a `pending`/`fail` result, since only
  `ci-gates-passed` existed as a stage and implied success — clarified that the gate result always
  lands in the `pr-published` entry's own `gates[]` array (which every entry already carries),
  reserving a separate `ci-gates-passed` stage entry for a later, dedicated resolution check outside
  this skill's own single-pass scope.
- 2026-09-10 — Fixed a third `cross-model-review` finding: the Git/GitHub Evidence Record's
  `provider` field was documented as always "the git-kit skill that performed the underlying
  operation," but `work-reopened` has no git-kit operation behind it (it's recorded alongside an
  ordinary Linear reopen via `linear-work-management`) — the field's own description required a
  provider attribution that stage can never truthfully supply. Carved out an explicit exception:
  `work-reopened` names the `workmanagement-kit` skill that determined the reopen was needed instead.
  `work-transition-reviewer`'s own Provider check updated to match, so it no longer flags a legitimate
  `work-reopened` entry as a missing `git-kit` attribution.
- 2026-09-10 — Fixed a second `cross-model-review` finding: the base Transition Contract's own
  `affected_record.system` schema literal still read `"notion | linear"`, never actually updated when
  the 2026-09-09 entry below extended the enum to include `"github"` — the schema and its own stated
  extension had drifted apart since the day the extension was written. Now reads
  `"notion | linear | github"`, matching the extension note.
- 2026-09-10 — Fixed a self-contradiction in the Git/GitHub Evidence Record found by
  `cross-model-review`: the schema's `superseded_by` field required mutating an *old* entry on every
  force-push/base-change repair, directly contradicting the same section's own "never overwritten"/
  "never edited in place" guarantees, and deviating from the Disposition Record precedent this record
  claimed to follow (which has no back-pointer field at all). Replaced `superseded_by` (set on the old
  entry) with `supersedes` (set only on the new entry, naming the earlier entry it invalidates) — the
  old entry is now genuinely never touched, matching Disposition Record's most-recent-wins convention
  literally, not just in name.
- 2026-09-09 — Added the Git/GitHub Evidence Record (`git-github-evidence`) and Repository Policy
  Profile for Wave 2 (`workmanagement-kit`'s Git/GitHub lifecycle bridge). Extended
  `affected_record.system`'s enum to include `"github"`. `versioned-configuration.json` bumped to
  schema version 2, adding `github`/`repository_policy` fields shipped `unconfigured`/`null` by
  default, same shippable-defaults-plus-local-override model as every existing field. `pr-merged` and
  this plugin's Linear closure remain distinct writes, matching Wave 1's already-established rule that
  `work-closed` is the only completion transition.
- 2026-08-31 — Initial version. Host profile and versioned configuration ship with `unconfigured`/
  `null` defaults (Foundational Setup — connector installation, workspace/team scoping, test
  scopes — is a separate task from creating these files; see `README.md`'s Status section).
- 2026-08-31 — Local Override section corrected: clarified the merge is deep at the operation
  level (an override naming one operation must not drop the others' `unconfigured` defaults), and
  added the tracked-vs-untracked trust-boundary check this file's `support_status`/scope claims
  require before being honored — found by automated PR review, this file previously and incorrectly
  claimed no such check was needed.
- 2026-08-31 — Transition Contract scoped explicitly to single-write evidence only, with a stated
  next-write convention (plus a terminal-write exception) resolving the causality gap between
  "verification_evidence describes a post-write read-back" and "the contract lives inline on the
  same write it's evidence for." Added the new Disposition Record mechanism
  (`disposition-history`) for multi-item batch outcomes against one source record. Clarified that
  cross-system links are represented by the already-shipped `notion-link`/`linear-link` entity
  fields, not this contract. Closes GitHub issue #254.
- 2026-08-31 — Added the `open-item-source` companion field (on the follow-up Issue, set as part
  of its own creation write) so a follow-up keeps a persisted source link even if the separately-
  approved Disposition Record write is later declined or fails — found by cross-model review on
  this same issue's fix.
- 2026-08-31 — `notion.databases` reshaped from a single flat record-type-to-ID map into
  `{test: {...}, prod: {...}}`, each nested map keyed by record type — the flat map had no way to
  represent both environments' resolved database IDs at once. Found live during Foundational Setup
  (`.draft/prompts/workmanagement-kit/foundation-setup-wave1.md`): Bootstrap resolved 7 test + 7
  prod database IDs, and the previously-documented flat shape could only hold one set.
