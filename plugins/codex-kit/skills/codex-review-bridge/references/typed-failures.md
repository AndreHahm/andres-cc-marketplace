# Typed failures

The bridge never returns an empty findings list to signal failure — every failure is one of the categories `scripts/lib/codex-exec.mjs`'s `FAILURE_CATEGORIES` defines, documented once in `codex-prompt-protocol/references/error-taxonomy.md` and not restated here (that file is canonical for the category list itself, to avoid this file's copy drifting out of sync — see its own "Not a failure category" note for why `incomplete_inspection` isn't among them).

## Bridge-specific presentation

Unlike the interactive components (`codex-rescue`/`codex-verify`/`codex-research`/the review commands), which surface a failure as prose, this bridge returns the category as a structured object: `{ ok: false, category, detail }`. `detail` carries the concrete evidence (truncated stderr, the specific semantic check that failed, etc.) — never just the bare category name alone.

## Two rules specific to this bridge

- `isolation_profile_unavailable` is **never silently substituted with `danger-full-access`** — the caller decides whether to fall back, this bridge only reports the failure.
- `semantic_validation_failure` triggers only for the checks `references/semantic-validation.md` documents as **currently implemented** — that file's own "Not yet implemented" list is authoritative on which checks aren't enforced yet; don't assume every field `references/envelope-schema.md` describes is mechanically verified.
