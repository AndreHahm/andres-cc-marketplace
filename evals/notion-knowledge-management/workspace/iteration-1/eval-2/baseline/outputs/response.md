# Decision Recorded: promptlibrary-kit In-Repo Copy — Read-Only Mirror (not Dual-Write)

**Decision:** `promptlibrary-kit`'s in-repo copy of repo-specific prompts will be a **read-only
fallback mirror** synced from Notion, not a dual-write design (i.e., not an independently editable
local copy that reconciles/proposes changes back to Notion).

## Where this is recorded

I located the existing design document for `promptlibrary-kit` at:

`.draft/_ready/promptlibrary-kit/new-plugin/2026-08-30-prompt-library-concept.md`

This decision is **already fully recorded there**, under the "Second Verification Pass (2026-08-30)"
section, item 1:

> **Mirror model: dual-write → read-only fallback mirror (adopted).** The prior design let a
> developer edit the in-repo copy directly, with a reconciliation pass proposing that edit back
> to Notion. Codex's independent copy redesigned this as a strict read-only fallback mirror:
> Notion is the only edit path; a local file edit is drift that the next sync silently overwrites
> and never proposes to Notion. ... This pass adopts the read-only-mirror design and applies it
> consistently in every section below, closing that contradiction.

The decision is then carried consistently through the rest of that document:
- **Purpose** — "a read-only fallback mirror inside this repository ... not an independent editing surface."
- **Authority Model** table — the in-repo mirror is listed as "Repo (subordinate, read-only fallback — refreshed from Notion, never written back)."
- **In-Repo Copy and Mirror Synchronization** / **Mirror Rules** — "Notion is the only edit path. Local files are managed fallback data; direct edits are local drift and `prompt-sync` repairs them from Notion." No background sync; "Direct local-file edit" always maps to "Notion → mirror on next sync ... never propose it to Notion."
- **Confirmation and Safety** — "Mirror files are fallback data. Direct edits are local drift and do not mutate Notion; `prompt-sync` restores the Notion-authoritative snapshot."
- **Acceptance Criteria** — explicitly requires "a direct local-file edit is drift that is never proposed to Notion."

## What I did

Since the document already states this exact decision consistently and unambiguously across every
relevant section (Purpose, Authority Model, Mirror Rules, Mirror Synchronization table,
Confirmation and Safety, and Acceptance Criteria), I did **not** make an edit — adding a duplicate
"decision" note on top of content that already says the same thing would be redundant and risks
drifting out of sync with the existing wording (against this repo's "surgical changes" /
"simplicity first" conventions).

## If you intended something different

A few possibilities I want to flag rather than guess past:

1. **If this decision was already made and you just wanted confirmation it's captured** — it is,
   at the location above. No further action needed.
2. **If you intended a *new* decision to override something currently different** — I didn't find
   any other document or code describing a dual-write design for `promptlibrary-kit` that would
   need to be changed to match. The only design doc I found already matches your statement.
3. **If you want this decision logged somewhere else** (e.g., a dedicated decision log, a GitHub
   issue, a Notion page, or a changelog entry) rather than relying on it living inside the concept
   draft — let me know the target location/format and I'll add it there. I didn't take that step
   unprompted since no decision-log convention or location was specified for this plugin, and
   guessing wrong would create a second, possibly inconsistent, record of the same decision.

**Note on scope:** I did not consult or read anything under `plugins/workmanagement-kit/` for this
task, per instructions — this response is based on the `promptlibrary-kit` draft document and
general judgment only. `promptlibrary-kit`'s design does depend on `workmanagement-kit` for Notion
access (per the draft), so if `workmanagement-kit`'s own documents also need this decision
reflected, that would need a separate check I did not perform here.
