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
    "databases": {}
  },
  "linear": {
    "organization_id": null,
    "production_team_id": null,
    "test_team_id": null
  }
}
```

- `notion.databases` — a map from Notion record type (`idea`, `decision`, `proposed-goal`, `note`,
  `research`, `report`, `outcome-learning`) to that type's resolved database ID, populated
  incrementally as Bootstrap resolves each type — never required to be fully populated at once.
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
  "affected_record": {"system": "notion | linear", "stable_id": "string"},
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

## Change Log

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
