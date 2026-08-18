# What `review.md` says to do when the envelope-schema file doesn't exist

## Source

`plugins/git-kit/skills/cross-model-review/prompts/review.md`, **## Output** section (lines 73–94).

## The fallback instruction

The Output section's exact text (lines 75–80):

> Return findings matching the required JSON schema exactly (`contract_version`, `dispatch`,
> `provenance`, `findings[]`, `verdict`, `inspection_limits`). See
> `plugins/codex-kit/skills/codex-review-bridge/references/envelope-schema.md` for the authoritative
> field list **when `codex-kit` is installed**; git-kit doesn't bundle its own copy, so when it isn't
> (e.g. this run is Claude-only, single-model mode — see SKILL.md's resolver step 3), use this
> self-contained summary instead: ...

So the prompt does **not** treat `envelope-schema.md` as a hard external dependency it blindly trusts to exist. It explicitly frames the reference path as conditional — "the authoritative field list **when `codex-kit` is installed**" — and states plainly that "git-kit doesn't bundle its own copy" of that schema. For the case where the path doesn't exist (codex-kit not installed at all, e.g. a Claude-only/single-model run per the SKILL.md resolver's step 3), the instruction is to fall back to a **self-contained summary written directly into this prompt file itself**, rather than trying to fetch, resolve, or otherwise depend on the missing file.

In other words: the fallback isn't "search elsewhere" or "fail/error out" — it's "use the inline field list that follows in this same section," which the prompt then spells out completely in the remainder of the Output section (lines 80–93).

## Per-finding fields the fallback summary covers

Per lines 80–93, the self-contained fallback summary covers the following per-finding fields:

1. **`id`** — unique within the envelope.
2. **`severity`** — one of `critical`/`major`/`minor`, to be assigned honestly:
   - `critical` = data loss/security/crash on a normal path
   - `major` = wrong behavior on a common path, or a real correctness/security issue on an edge case
   - `minor` = everything else worth surfacing
3. **`axis`** — a short free-text category, e.g. `security`, `correctness`, `api-misuse`, `performance`, `maintainability`.
4. **`location`** — a single `"file:line"` string; the finding's primary citation.
5. **`components`** — either `null` or an array of *other* file paths involved, used only when a finding is inherently about a relationship between multiple files (never a substitute for `location`).
6. **`evidence`** — what was actually observed, not just a conclusion.
7. **`finding`** — the claim itself: what's wrong and why it matters.
8. **`fix`** — a specific recommended remediation.
9. **`confidence`** — `high`/`medium`/`low`, reflecting the reviewer's own certainty, independent of what the later cross-examination pass does with it.

## Top-level `verdict`, also covered by the fallback

The same paragraph (lines 90–93) also defines the envelope's top-level `verdict` field as part of this self-contained summary:

- `verdict` is `approve` or `needs-attention` — described as "this skill's own convention layered on the schema's free-string `verdict` field," since the (unavailable) schema itself only requires a deterministic pass/fail rule but doesn't define this specific enum.
- `approve` when no findings clear the evidence bar; `needs-attention` when at least one does.

## Fields *not* itemized by the fallback

The fallback summary is explicitly scoped to per-finding fields (plus the `verdict` convention) — it does not redefine the envelope's other top-level fields named earlier in the same sentence (`contract_version`, `dispatch`, `provenance`, `findings[]`, `inspection_limits`). Those are named as required top-level keys of the schema (line 75) but are not given their own field-by-field definitions in the fallback text; only `envelope-schema.md` (when present) would presumably define those in full.
