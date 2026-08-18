# Does Preflight step 2 catch an out-of-repo symlink before Codex dispatch?

**Yes.** Preflight step 2 in `plugins/git-kit/skills/cross-model-review/SKILL.md` (lines 120–157)
explicitly detects and excludes exactly this case, and it does so during Preflight — i.e. before
the Codex dispatch resolver or Phase 1's Codex pass ever run.

## Where the detection happens

Step 2 first computes the changed-file list for `--target-paths` via
`git diff --name-only "$MERGE_BASE" [-- "$SCOPE"]`, and excludes anything that fails a charset
check or no longer exists on disk (deleted paths). Immediately after that, the skill adds a
dedicated symlink check (lines 127–135):

> "**Also exclude a path that's a symlink resolving outside the repository.** `realpath -- <path>`
> each candidate; if the result doesn't start with `$(git rev-parse --show-toplevel)` (this step
> runs before step 4 resolves `$REPO_ROOT` as a named variable — re-run the same command inline
> here rather than depending on a not-yet-assigned value), exclude it the same way — both dispatch
> scripts canonicalize target paths before their own containment check and reject the *entire
> dispatch* on one such entry (a `non_zero_exit`/containment-violation typed failure), which would
> otherwise force an unnecessary single-model fallback for the whole review over one symlink. Keep
> it in Claude's own native review regardless (Claude has no such containment constraint); only the
> Codex-facing `--target-paths` list is affected."

So the mechanism is: `realpath -- <path>` is run on every candidate changed file, and the resolved
path is compared against `git rev-parse --show-toplevel` (re-run inline rather than relying on the
`$REPO_ROOT` variable, since that variable isn't assigned until step 4). Any candidate whose
resolved target falls outside the repo root is dropped from the list that becomes
`--target-paths` — the same treatment as a charset-invalid or deleted path gets.

This exclusion is also carried into the Codex-facing diff *text*, not just the `--target-paths`
list. Step 2 goes on to say (lines 137–148) that if anything was excluded, a separate
`CODEX_DIFF`/`CODEX_DIFF_STR` must be built from only the eligible files, and every place the skill
embeds diff content into a Codex-bound instruction file (Phase 1 and Phase 2) must use
`$CODEX_DIFF_STR`, never the full `$DIFF_STR` — otherwise Codex could read/cite the excluded
symlink's diff content in prose even though it was excluded from `--target-paths` proper.

## What would happen if this exclusion didn't exist

The skill states the consequence directly: both `codex-review-bridge` and
`codex-windows-guardrails` "canonicalize target paths before their own containment check and reject
the *entire dispatch*" the moment one target path resolves (post-canonicalization) outside the
repo root — a `non_zero_exit`/containment-violation typed failure. This isn't a per-file rejection;
it fails the *whole* Codex call for that phase. Per the Codex dispatch resolver section (lines
218–268), a typed failure like this would be treated as "any other typed failure" (resolver step 3,
lines 250–256), which forces the `AskUserQuestion` "Codex unavailable" fallback — the reviewer
would be asked whether to proceed single-model (Claude only) or stop, for the *entire diff*, not
just the one bad path. The skill calls this out explicitly as the failure mode it's designed to
avoid: "which would otherwise force an unnecessary single-model fallback for the whole review over
one symlink" (step 2, lines 132–133).

If, additionally, the excluded path had been the *only* changed file (or all changed files were
symlinks resolving outside the repo), step 2's later clause (lines 150–157) covers that: with zero
eligible files after exclusions, the skill skips Codex entirely and enters single-model mode before
even attempting a dispatch — because `bridge-invoke.mjs` rejects an empty `--target-paths` outright
as a missing required argument, so attempting it would be guaranteed to fail anyway. In that case
Phase 3's `inspection_limits` records the reason as "zero Codex-eligible paths in this diff" rather
than "Codex unavailable" (Phase 3, lines 400–402), since the two carry different meaning for a
report reader.

## Is the excluded file still reviewed at all?

**Yes, by Claude — no, by Codex.** Step 2 says explicitly: "Keep it in Claude's own native review
regardless (Claude has no such containment constraint); only the Codex-facing `--target-paths` list
is affected." Claude's Phase 1 pass reviews the full, unfiltered diff (`"${DIFF[@]}"`/`$DIFF_STR`,
per Phase 1's "Claude's native pass" instructions, lines 304–308), so the symlink's diff content is
still inspected by Claude. Codex, however, never sees it as a `--target-paths` entry and — per the
`CODEX_DIFF_STR` construction — never sees its diff text embedded in its instruction files either.

This asymmetry then propagates into Phase 2 and Phase 3:

- **Phase 2** explicitly instructs dropping any Claude Phase 1 finding whose `location` (or any
  entry in its `components` array) falls on a path step 2 excluded, *before* it's ever assembled
  into Codex's challenger instruction file (lines 358–368) — because the bridge's
  `semanticallyValidate` would reject Codex's *entire returned envelope*, not just that one
  finding, if a classification entry cites an excluded path.
- **Phase 3** assigns any such Claude-only finding to the **Medium** confidence tier, explicitly
  noting it is "structurally single-sided, never cross-examined, not a gap to flag" (lines
  427–431) — distinct from the "gap" case where a challenger simply failed to address a finding.
  Phase 3 also requires noting the exclusion itself under `inspection_limits` (lines 437–441): "the
  Preflight step 2 charset/deleted-path exclusion if it happened, any Claude finding dropped from
  the Codex challenge for that same reason..."

## Summary

| Question | Answer | Citation |
|---|---|---|
| Detected before Codex dispatch? | Yes — `realpath` check against repo root, run in Preflight step 2, before the resolver/Phase 1 Codex call | SKILL.md lines 127–135 |
| Excluded from `--target-paths`? | Yes, same treatment as charset/deleted-path exclusions | lines 120–135 |
| Also excluded from Codex-embedded diff text? | Yes, via separate `CODEX_DIFF_STR` | lines 137–148 |
| What breaks without the check? | Both dispatch scripts reject the *entire* Codex dispatch on a containment violation, forcing an unwanted full single-model fallback (or, if it's the only file, a guaranteed `bridge-invoke.mjs` argument-validation failure) | lines 128–133, 152–156, resolver step 3 (lines 250–256) |
| Still reviewed at all? | Yes, by Claude's native pass (no containment constraint applies to Claude); not by Codex; any resulting Claude-only finding is capped at Medium confidence and flagged in `inspection_limits`, not silently dropped | lines 133–135, 358–368, 427–431, 437–441 |
