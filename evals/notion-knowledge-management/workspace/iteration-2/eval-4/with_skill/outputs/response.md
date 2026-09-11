# Task

> Record a decision: we're deprecating the legacy CSV importer in favor of the new bulk API endpoint,
> effective next release.

This is a direct request to capture a new **Decision** record — squarely `notion-knowledge-management`'s
job (not `status-and-learning`, since nothing here is a post-hoc outcome/learning summary derived from
Linear facts; not `linear-work-management`, since nothing is being promoted into Linear execution state).

I followed the skill's Quick Start procedure. Step 1 (resolve the connector) turned up a hard blocker, so
I stopped there rather than proceeding to a live write — full detail below.

---

## Step 1 — Resolve the connector through the shared host profile

Per the skill's "Resolving the connector" section: tool presence is never proof of permission — only
`host-profile.json`'s own `support_status`/`verified_at` fields confirm a read or write is actually
sanctioned, and that file ships with every operation defaulting to `unconfigured` until an installer
activates it via `.claude/workmanagement-kit.local.json`.

**I read the plugin's real files in this worktree to check current state** (local file reads only — no
MCP/Notion tool called):

`Read(plugins/workmanagement-kit/host-profile.json)`:
```json
{
  "version": 1,
  "operations": {
    "notion.read":  {"support_status": "unconfigured", "verified_at": null, "connector": null, "workspace_id": null},
    "notion.write": {"support_status": "unconfigured", "verified_at": null, "connector": null, "workspace_id": null},
    "linear.read":  {"support_status": "unconfigured", "verified_at": null, "connector": null, "organization_id": null, "team_ids": []},
    "linear.write": {"support_status": "unconfigured", "verified_at": null, "connector": null, "organization_id": null, "team_ids": []}
  }
}
```

`Read(plugins/workmanagement-kit/versioned-configuration.json)`:
```json
{
  "version": 2,
  "notion": {
    "production_workspace_id": null,
    "test_workspace_id": null,
    "databases": { "test": {}, "prod": {} }
  },
  ...
}
```
No database ID is resolved for the `decision` record type in either the `test` or `prod` environment —
Bootstrap has never been run for this record type either, independent of the connector question below.

**Before assuming these shipped "unconfigured" defaults are stale**, I checked whether an installer's
local override (`.claude/workmanagement-kit.local.json`) exists and is genuinely untracked, per
`FOUNDATION_CONTRACTS.md`'s Local Override trust-boundary check — the same discipline `commit`'s own
trust check uses, and mandatory here since `notion-knowledge-management/SKILL.md` explicitly says not to
honor that file's claims without running it first:

`Bash(git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json")`
→ `error: pathspec ':(top,literal).claude/workmanagement-kit.local.json' did not match any file(s) known to git` (exit 1)

`Bash(ls -la .claude/workmanagement-kit.local.json)` → `No such file or directory`

Result: the file is not tracked, and — unlike a normal "confirmed-untracked, honor its contents" outcome
— **it does not exist on disk in this worktree at all**. There is nothing to override with. The shipped
`unconfigured` defaults stand for all four operations, including `notion.read` and `notion.write`.

**Cross-check against the plugin's own README**, which is worth flagging explicitly rather than silently
reconciling: `plugins/workmanagement-kit/README.md`'s Status section states *"This repository's own
installation completed that activation live during Foundational Setup... all four
`notion.read`/`notion.write`/`linear.read`/`linear.write` operations are `verified` in this repo's own
local override, with real resolved Notion workspace/database IDs..."* — which contradicts what I can
actually verify in this working directory. I'm not treating the README's narrative claim as authoritative
over a live check (per the skill's own "tool presence/doc claims are never proof of permission" framing),
but the likely explanation is mundane and already a known issue in this environment: `.claude/*.local.json`
files are gitignored, and a fresh `git worktree` does not copy gitignored files/directories from the
primary checkout — only `settings.local.json`/`CLAUDE.local.json` are auto-copied. This worktree
(`workmanagement-kit-downstream-qa`) most likely just never received a copy of the primary checkout's
`.claude/workmanagement-kit.local.json`. I'm disclosing this as my best guess at *why*, not asserting it
as confirmed — the skill's own procedure doesn't let me act as if the override were present just because
I have a plausible explanation for its absence.

**Conclusion: `notion.read` and `notion.write` both read as `unconfigured` in this session.** Per
SKILL.md: *"until an operation's `support_status` reads `verified`, no write may proceed on the
assumption that a sanctioning check happened."* The Host Profile section is explicit that this check
covers reads too ("Every skill that reads or writes Notion/Linear must check this file's
`support_status`/`verified_at` fields for the specific operation before calling the connector, even when
the connector tool itself is callable"). So I am **not** calling any of:
- `mcp__claude_ai_Notion__notion-search` / `notion-fetch` / `notion-query-data-sources` (Step 2's
  "read the relevant record(s), if any exist" — skipped; I cannot check whether a related/prior Decision
  about the CSV importer already exists)
- `mcp__claude_ai_Notion__notion-create-pages` (the actual write)

Doing so would be acting on a connector call the plugin's own gate has not sanctioned for this session,
which the skill treats as unconditionally blocking — there is no severity threshold or "looks safe" carve-out here.

---

## What I would ask the user, given this blocker

Per CLAUDE.md's "Think Before Coding" (surface confusion, don't guess past a real blocker) and the
Gotchas section's "ambiguous target = stop, don't guess" precedent, I would stop here and raise this via
`AskUserQuestion` rather than either fabricating a successful write or silently giving up:

```
AskUserQuestion({
  questions: [{
    question: "notion.read/notion.write both show `unconfigured` in this worktree's host-profile.json, and .claude/workmanagement-kit.local.json isn't present here at all (likely just not copied into this worktree — gitignored files don't come along with `git worktree add`). How do you want to proceed?",
    options: [
      { label: "Copy override file", description: "Copy the primary checkout's .claude/workmanagement-kit.local.json into this worktree, then retry" },
      { label: "Run Foundational Setup", description: "This connector has genuinely never been verified for this installation — walk through Foundational Setup now" },
      { label: "Prepare content only", description: "Skip live Notion entirely for now — just give me the fully-drafted Decision record content so I can enter it myself" },
      { label: "Something else", description: "Let me clarify" }
    ]
  }]
})
```

I would wait for a real answer before calling any connector tool — this isn't a case where "make the
reasonable call and keep going" applies, since which of these the user wants changes what I do next in a
way I can't infer, and a wrong guess here risks writing (or claiming to write) against an unsanctioned
connector.

**Separately, once unblocked**, the record content itself has one more open question I'd also raise (not
bundled into the same `AskUserQuestion` call — batching unrelated decisions into one multi-question call
risks the harness's per-call option/question caps and makes each decision harder to reason about
independently, so I'd ask it as its own follow-up once the connector question is resolved): the Decision
State Machine requires every new Decision to start in `proposed` state (a `Propose` action, itself
approval-gated) — `Accept` is a distinct, separately-approved action, never a default side effect of
creating the record. The user's phrasing ("we're deprecating... effective next release") reads like a
decision that's already settled, not merely floated for consideration, so I would not silently assume
`proposed` is what they want:

```
AskUserQuestion({
  questions: [{
    question: "This Decision — record it as `proposed` (pending a separate Accept step later), or create it and then immediately run Accept as a second approved write, since \"effective next release\" reads like this is already settled?",
    options: [
      { label: "Proposed only", description: "Create with decision-state=proposed; Accept happens later as its own approved action" },
      { label: "Create + Accept now", description: "Create as proposed, then immediately request approval for a second write that transitions it to accepted" }
    ]
  }]
})
```

---

## Record content I have prepared (preview only — not yet written anywhere)

Building this preview requires no approval (per Confirmation and Safety: "previewing what a capture would
look like before writing" needs none) and doesn't touch the connector, so I did this regardless of the
blocker above, per `references/notion-record-types.md`'s Decision property table:

| Property | Value |
|---|---|
| `title` | Deprecate legacy CSV importer in favor of bulk API endpoint |
| `context` | The legacy CSV importer is the older, manual ingestion path. A new bulk API endpoint now covers the same use case with better reliability and automation potential. Maintaining both indefinitely duplicates support and maintenance surface. |
| `alternatives` | (1) Keep the CSV importer supported indefinitely alongside the bulk API; (2) deprecate the CSV importer now, effective next release, steering users to the bulk API — **chosen**; (3) remove the CSV importer immediately with no deprecation window. |
| `consequences` | Starting next release, the CSV importer is marked deprecated; users/integrations currently depending on it should migrate to the bulk API endpoint; docs and any in-product messaging referencing the CSV importer need updating; an actual removal date was not specified in the request and should be confirmed separately. |
| `decision-state` | `proposed` (default per the Decision State Machine) — **open question above**: user may want `accepted` instead |
| `supersedes` / `superseded-by` | Unknown — Step 2's read (checking for a prior related Decision about the CSV importer) could not run; this must be re-checked once `notion.read` is verified, before the write, in case this should instead be framed as superseding an existing Decision |
| `related-artifact` | None provided by the request |
| `linear-link` | None (not this skill's job to populate — `work-linking` populates this only if/when `idea-to-implementation` later promotes this Decision) |
| `disposition-history` | None (not applicable at creation) |
| `source` | Direct user request, captured via `notion-knowledge-management` |
| `related-record` | None known (pending the blocked read above) |
| `authority` | `notion` |
| `owner` | andre.hahm@me.com |
| `date` | 2026-09-11 |
| `transition-id` | Not yet generated — only assigned at the moment of an actual write, per the Transition Contract |

**Safety scan of this content:** checked for anything that looks like a credential, token, or
third-party personal data per Confirmation and Safety's requirement to surface that in the approval
preview — none present. No special acknowledgment needed on that front.

I did **not** dispatch `work-intake-classifier` for independent classification help — this capture is
small and unambiguous (a single, clearly-scoped Decision), not the "large or unclear capture" case that
section gates on, so there's nothing to ask permission for there.

---

## What I would do once both blockers clear (for the record — not executed)

Once (a) the connector question above is resolved and `notion.read`/`notion.write` genuinely read
`verified` for this session, (b) a `decision` database ID is resolved in `versioned-configuration.json`
for the target environment, and (c) the propose-vs-accept question is answered:

1. `mcp__claude_ai_Notion__notion-search` / `notion-fetch` — check for an existing/related Decision about
   the CSV importer (resolves the `supersedes` question above; if found, this becomes a **Supersede**
   flow instead of a fresh **Propose**, which changes the write sequencing per the Decision State Machine
   — new Decision record first, then flip the old one's state, reporting explicitly if the state flip
   fails after the new record was created).
2. Present the finished record (table above, with `decision-state` and `supersedes` resolved) via
   `AskUserQuestion` for live approval — required unconditionally for creating any Decision record, no
   exception for how low-risk it looks.
3. On approval: `mcp__claude_ai_Notion__notion-create-pages` to write it (and, if Accept was also
   requested, a second approved write transitioning `decision-state` to `accepted`, per the Decision State
   Machine's requirement that Accept is its own gated action, appending rather than overwriting the
   proposal text).
4. Read back via `notion-fetch` to confirm the write actually landed as intended — never assumed from a
   non-error return.
5. Record the resulting transition per `FOUNDATION_CONTRACTS.md`'s Transition Contract, embedded on the
   record itself (`transition_id`, `operation_id`, `affected_record`, `source_plugin: "workmanagement-kit"`,
   `recorded_at`), following the next-write convention for `verification_evidence` — since this is very
   likely this record's only write for now (unless Accept is also requested in the same pass), the
   terminal-write exception applies: one additional metadata-only write records this write's own
   `verification_evidence`, needing no fresh approval since it only touches the evidence field.

None of step 1–5 was executed in this session — only the preview above was built.

---

## Summary

- **Blocked before any live Notion call**: `notion.read`/`notion.write` both read `unconfigured` in this
  worktree, and the local override file that would activate them (`.claude/workmanagement-kit.local.json`)
  is absent here entirely — most likely a gitignored-file-not-copied-into-worktree gap, not a genuine
  unconfigured installation, but I verified rather than assumed, and the skill's gate doesn't let me act
  on a plausible explanation instead of a confirmed `verified` status.
- **Nothing was written to Notion.** No `notion-search`/`notion-fetch`/`notion-create-pages` call was
  made.
- A full Decision-record preview is ready to go (table above), with two open questions flagged for the
  user: (1) how to unblock the connector for this worktree, and (2) whether to record this as `proposed`
  only or immediately follow with an approved `Accept` write, given the "effective next release" phrasing.
