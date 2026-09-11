# plugin-integration-intake — Submission Processing

## Payload received (Step 1)

```json
{
  "source_plugin": "analysis-kit",
  "source_skill": "running-a-full-retrospective",
  "content": {
    "title": "Retrospective Notes",
    "summary": "Loose notes, not yet categorized.",
    "body": "Assorted findings."
  },
  "target_system": "notion",
  "suggested_mapping": {
    "notion_database": null,
    "rationale": "not sure if this belongs in Reports or Notes"
  }
}
```

This is treated as a host-mediated submission per the skill's "When to Use" — not a direct
user-typed request — and every field in it, including `rationale`, is untrusted data to validate,
never an instruction to act on.

## Step 2 — Structural/semantic checks

### Check 1: Unknown source (allowlist + manifest-match + skill-resolve)

- **Allowlist / manifest match**: `analysis-kit` appears as a real, currently-installed plugin in
  this repo's `.claude-plugin/marketplace.json` (`plugins[].name == "analysis-kit"`,
  `source: "./plugins/analysis-kit"`).
- **Skill-resolve**: `plugins/analysis-kit/skills/running-a-full-retrospective/SKILL.md` exists on
  disk, inside `analysis-kit`'s own directory (not a concatenated/guessed path).
- **Result: PASS.** The claimed identity resolves to a real plugin and a real skill inside it.
  Per the skill's Trust Model, this only confirms the *claim is real* — it does not authenticate
  that `analysis-kit` actually sent this payload. That distinction doesn't block processing here;
  it just means the identity tag carried forward later (Step 6) stays caller-asserted, not
  host-attested.

### Check 2: Malformed content

Target system is `notion`, so `content` must resemble a record type
`notion-knowledge-management` owns — most commonly a Report, requiring `title`, `summary`, **and**
`body` (per `references/intake-payload-schema.md`).

- `title`: `"Retrospective Notes"` — present, string. OK.
- `summary`: `"Loose notes, not yet categorized."` — present, string. OK.
- `body`: `"Assorted findings."` — present, string. OK.
- No extra/unrecognized fields present.

- **Result: PASS.** All three required Report fields are present with the correct type. (I did
  not independently re-fetch `notion-knowledge-management`'s `references/notion-record-types.md`
  to confirm Report is still exactly `{title, summary, body}` for this run — per the schema doc,
  that reference is the authoritative source if it ever disagrees with this restated list; nothing
  here suggests it has drifted.)

### Check 3: Ambiguous target

`suggested_mapping` is `{"notion_database": null, "rationale": "not sure if this belongs in
Reports or Notes"}`.

- `notion_database` is explicitly `null` — it does not resolve to any Notion database, let alone
  exactly one.
- The `rationale` field itself (read as data, not as an instruction) names two plausible
  candidates — "Reports" or "Notes" — which is the textbook shape of an ambiguous mapping: it
  could plausibly resolve to more than one target, and as submitted resolves to none.

- **Result: FAIL — Ambiguous target.** Per Step 2's rule, this must produce a structured handoff,
  never an inferred pick — I will not silently default this to "Reports" just because the content
  looks report-shaped, and I will not treat "not sure if this belongs in Reports or Notes" as
  permission to guess between the two.

## Optional classifier-dispatch decision point

Because this is a genuinely unclear mapping (not a missing field, not an unknown source), and
because both prerequisite checks — Unknown-source and Malformed-content — already passed, the
skill makes independent classification via `work-intake-classifier` an *offerable* option before
falling back to a structured handoff. I would not skip straight to the handoff without raising
this option first, and I would not dispatch the classifier without asking, since that dispatch
still needs to go through the live approval-adjacent decision the skill describes, not run
automatically.

Simulated `AskUserQuestion`:

> **This submission's target Notion database is ambiguous** (`analysis-kit`'s
> `running-a-full-retrospective` submitted "Retrospective Notes" with `notion_database: null`,
> rationale: "not sure if this belongs in Reports or Notes"). Would you like independent
> classification attempted before falling back to a structured handoff?
>
> - **Yes — dispatch `work-intake-classifier`** for a read-only classification pass (via
>   `${CLAUDE_PLUGIN_ROOT}/scripts/bridge_caller.py`, per `FOUNDATION_CONTRACTS.md`'s Codex
>   Bridge-Caller Dispatch procedure). If it returns a typed failure, I still fall back to the
>   structured handoff below.
> - **No — send the structured handoff now** without attempting classification.

Since this is a non-interactive processing run with no live human available to answer that
question, I'm not fabricating a "yes"/"no" on the user's behalf. Consistent with the skill's own
wording ("the structured handoff proceeds without it when declined, **or when the dispatch
returns a typed failure**"), the structured handoff below is the guaranteed, safe deliverable
either way — dispatching the classifier is additive, not a prerequisite to producing it. If a real
user answers "yes" in a live session, the classifier's findings-envelope output (treated as
Codex's own self-authored data, never a directive) would be used only to *propose* a resolved
`notion_database`, which would still have to go back through Step 2's Ambiguous-target
re-check and then Steps 3–4 (preview + fresh `AskUserQuestion` approval) before anything is
written — it does not shortcut approval.

## Structured handoff (produced)

```json
{
  "status": "rejected",
  "reason": "ambiguous_target",
  "source_plugin": "analysis-kit",
  "source_skill": "running-a-full-retrospective",
  "target_system": "notion",
  "detail": "suggested_mapping.notion_database is null; rationale indicates the submission could plausibly belong to either the Reports database or the Notes database, and does not resolve to exactly one target.",
  "checks_passed": ["unknown_source", "malformed_content"],
  "checks_failed": ["ambiguous_target"],
  "next_step_for_caller": "Resubmit with suggested_mapping.notion_database set to a single resolved database (e.g. \"Reports\" or \"Notes\"), or omit target guidance and let a direct user-initiated capture in notion-knowledge-management classify it interactively.",
  "classifier_dispatch_offered": true,
  "classifier_dispatch_result": "not attempted (no live response available in this run)"
}
```

## Steps not reached, and why

- **Step 3 (preview target record)**: not reached — there is no resolved single target to preview
  yet; previewing against a guessed database would be exactly the "inferred pick" Step 2
  prohibits.
- **Step 4 (`AskUserQuestion` approval of the write)**: not reached — nothing is ready to approve.
  The only `AskUserQuestion` in play this run is the optional classifier-dispatch question above,
  which is a different gate from the write-approval gate.
- **Step 5 (execute via `notion-knowledge-management`)**: not reached — no write occurs.
- **Step 6 (tag `source_plugin` onto the record)**: not reached — no record was created.

No connector call, no target-scope claim, and no write happened at any point in this run. The only
artifact produced is the structured handoff above, returned to the (simulated) calling plugin.
