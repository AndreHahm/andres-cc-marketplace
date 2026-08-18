# Does Codex's `review_for_codex.md` see the same diff text as Claude's native pass?

**No — they are not the same.** Claude's native pass sees the full diff, including the deleted
file's removal hunk. Codex's Phase 1 instruction file (`review_for_codex.md`) sees a *narrower*
diff that omits the deleted file entirely. The skill builds this asymmetry deliberately, via a
second, separately-scoped diff variable computed specifically because a path was excluded in
Preflight step 2.

## Walkthrough of the mechanism

### 1. Preflight step 2 excludes the deleted file from `--target-paths`

Preflight step 2 says:

> Compute the changed-file list for `--target-paths`: `git diff --name-only "$BASE...HEAD" [-- "$SCOPE"]`.
> `codex-review-bridge` validates each target path against `^[A-Za-z0-9._/-]+$` and
> `codex-windows-guardrails` additionally requires the path to still exist on disk — a path
> containing any other character, or a path the diff *deletes*, cannot go through either dispatch
> as-is. If any changed path fails that pattern or no longer exists, exclude it from
> `--target-paths` (note it in the final report as an inspection limit) rather than failing the
> whole run.

A deleted file, by definition, no longer exists on disk after the diff — so it fails the
"still exist on disk" requirement `codex-windows-guardrails` imposes, and it is excluded from
`--target-paths` for this run.

### 2. That exclusion forces a second, Codex-only diff variable to be built

The same step immediately continues (this is the load-bearing part):

> **Build a Codex-scoped diff text from the eligible paths only, kept separate from `$DIFF_STR`.**
> Both dispatch scripts validate a returned finding's `location` against `--target-paths` and
> reject the envelope if it falls outside that scope — but Phase 1/2 below embed diff text
> directly into Codex's instruction file as plain prose, which isn't scoped the same way.
> Embedding the full, unfiltered `$DIFF_STR` would let Codex read (and potentially cite) the very
> files just excluded from `--target-paths`, risking exactly that rejection. If anything was
> excluded above, compute `CODEX_DIFF=(git diff "$BASE...HEAD" -- <eligible files only>)` and
> `CODEX_DIFF_STR=$(printf '%q ' "${CODEX_DIFF[@]}")`; otherwise `CODEX_DIFF_STR="$DIFF_STR"`
> (nothing was excluded, so the two are identical). Use `$CODEX_DIFF_STR` — never `$DIFF_STR` —
> anywhere this document embeds diff text into a Codex-bound instruction file (Phase 1 and
> Phase 2). Claude's own native pass is unaffected and keeps using the full
> `"${DIFF[@]}"`/`$DIFF_STR` — this containment is a Codex dispatch constraint, not a
> review-scope reduction for Claude.

Because one file *was* excluded in this run (the deleted one), `CODEX_DIFF_STR` is **not** set
equal to `$DIFF_STR` — it is recomputed from scratch as `git diff "$BASE...HEAD" -- <eligible
files only>`, i.e. the same base/head diff but re-run with an explicit pathspec that omits the
deleted file. Git simply never emits that file's deletion hunk when it isn't part of the
pathspec, so `CODEX_DIFF_STR` contains the diff for every changed file *except* the deleted one.

### 3. Where each variable actually lands

- **Claude's native pass (Phase 1):** "Claude already ran `"${DIFF[@]}"` in Preflight step 1, so
  the diff is already in context — no separate assembly needed here." This is the full,
  unfiltered diff from `"${DIFF[@]}"`/`$DIFF_STR`, run once in Preflight step 1 against the full
  changed-file set (deleted file included, since Preflight step 1's diff command has no
  `--target-paths`-style filtering — that filtering only affects what's passed to Codex's CLI
  flag and, per step 2, what's embedded in Codex's prompt text).

- **Codex's Phase 1 pass:** "`Read` `$RUN/review.md`, append a trailing `Review the diff:
  $CODEX_DIFF_STR` line to its content, and `Write` the result to `$RUN/review_for_codex.md`."
  This is explicitly `$CODEX_DIFF_STR`, not `$DIFF_STR` — so `review_for_codex.md` embeds the
  diff with the deleted file's hunk omitted.

- **Codex's Phase 2 pass** (for completeness, same mechanism applies): the
  `challenger_instructions_for_codex.md` assembly also inserts "a blank line, then `Review the
  diff: $CODEX_DIFF_STR`" — same narrowed variable, same omission.

### 4. Confirmed by the skill's own quality gate

The Testing & Validation section's quality-gates checklist states this as an explicit,
checkable invariant:

> - [ ] A Codex-bound instruction file never embeds diff text for a file Preflight step 2
>       excluded from `--target-paths` — `$CODEX_DIFF_STR` is used for every Codex-facing embed,
>       `$DIFF_STR` only for Claude's own native pass

This is exactly the scenario in the question: one file was excluded (deleted-by-the-diff case),
so this checklist item requires `review_for_codex.md` to omit that file's diff text while
Claude's native pass keeps it.

## Are they the same? Why not?

No. Concretely, for this run:

- **Claude's native review** operates over the complete diff, which includes the hunk showing
  the excluded file's deletion (Claude read `"${DIFF[@]}"` directly in Preflight step 1, and
  nothing in the skill narrows that for Claude — "Claude's own native pass is unaffected").
- **Codex's Phase 1 instruction file (`review_for_codex.md`)** embeds only `$CODEX_DIFF_STR`,
  which was recomputed in Preflight step 2 as `git diff "$BASE...HEAD" -- <eligible files
  only>` — a pathspec-restricted diff that structurally cannot contain the deleted file's hunk,
  because that file was never included in `<eligible files only>`.

## The mechanism that produces the difference

The difference is produced entirely by **Preflight step 2's `CODEX_DIFF`/`CODEX_DIFF_STR`
construction**, which exists specifically to prevent a trust/scope mismatch between two other
mechanisms:

1. `--target-paths` is the CLI-level scope both `codex-review-bridge` and
   `codex-windows-guardrails` use to validate a *returned finding's* `location` field — a finding
   citing a file outside `--target-paths` gets its envelope rejected.
2. The diff text embedded as plain prose in an instruction file (`review_for_codex.md`,
   `challenger_instructions_for_codex.md`) is **not** scoped by `--target-paths` at all — that
   flag only constrains the dispatch script's own post-hoc validation of findings, not what
   content Claude chooses to paste into the prompt.

Without step 2's fix, Claude could paste the *full* `$DIFF_STR` (including the deleted file) into
`review_for_codex.md` while simultaneously passing a `--target-paths` list that excludes that
file — Codex could then read and cite the deleted file in a finding, and that finding's envelope
would be rejected by the dispatch script's own `location`-vs-`--target-paths` check, silently
losing a finding (or worse, causing confusing partial failures). Step 2 closes that gap by making
the prompt-embedded diff text and the `--target-paths` list agree on the same eligible-file set,
via the separately-computed `CODEX_DIFF_STR`. Claude's native pass has no such constraint (there's
no `--target-paths`-style envelope validation for Claude's own in-session findings), so it
continues using the unfiltered `$DIFF_STR`/`"${DIFF[@]}"` from Preflight step 1 with no
narrowing.

## Where this shows up in reporting

This asymmetry is not meant to be silent. Preflight step 2 says to "note it in the final report
as an inspection limit," and Phase 3 explicitly folds it into the synthesis step: "Note any
`inspection_limits` from either side, including: the Preflight step 2 charset/deleted-path
exclusion if it happened...". So the final cross-model report for this run should disclose that
Codex's pass did not have visibility into the deleted file, while Claude's did — i.e., Codex's
review is scoped narrower than Claude's for this specific diff, and that's a known, declared
limitation of this run rather than an unnoticed gap.
