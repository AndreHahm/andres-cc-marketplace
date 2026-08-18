# Does Preflight step 6 detect `plugins/codex-kit/scripts/lib/codex-exec.mjs`?

**Yes.** Preflight step 6 is specifically designed to catch this file, and the SKILL.md even names
this exact path as the motivating example for why the check's regex is shaped the way it is.

## What step 6 actually does

From the SKILL.md (Preflight, step 6, lines 136–147):

> **Check whether the diff itself touches the Codex dispatcher scripts this skill is about to
> execute** — grep the Preflight step 2 changed-file list for `plugins/codex-kit/(.*/)?scripts/`.
> The optional `(.*/)?` group matters: it must also match
> `plugins/codex-kit/scripts/lib/codex-exec.mjs` — a shared executable both dispatch scripts import
> and run — not just the deeper `plugins/codex-kit/skills/<name>/scripts/*.mjs` paths; a pattern
> requiring an extra directory segment before `scripts/` misses that shared file entirely.

So the mechanics are:

1. **Input**: the changed-file list already computed in Preflight step 2
   (`git diff --name-only "$BASE...HEAD" [-- "$SCOPE"]`).
2. **Check**: grep that list for the regex `plugins/codex-kit/(.*/)?scripts/`.
3. **Why the `(.*/)?` group is required**: without it, the pattern would only match paths that have
   an extra path segment between `plugins/codex-kit/` and `scripts/` (e.g.
   `plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs`). The optional group
   lets the pattern match both that deeper shape *and* the shallower
   `plugins/codex-kit/scripts/...` shape where `scripts/` sits directly under `plugins/codex-kit/`.

## Does it match this specific path?

Walking the regex `plugins/codex-kit/(.*/)?scripts/` against
`plugins/codex-kit/scripts/lib/codex-exec.mjs`:

- `plugins/codex-kit/` matches literally.
- The optional group `(.*/)?` matches the empty string (zero occurrences) — it's optional, so it's
  allowed to consume nothing here.
- `scripts/` then matches the literal `scripts/` that immediately follows `plugins/codex-kit/` in
  the path.
- The remainder of the path (`lib/codex-exec.mjs`) is unconstrained by the pattern, so it's simply
  matched by nothing further (the grep only needs the pattern to appear as a substring/match within
  the line, not to consume the whole string).

So yes — `plugins/codex-kit/scripts/lib/codex-exec.mjs` matches. This is not a coincidence: the
SKILL.md explicitly calls out this exact file (`plugins/codex-kit/scripts/lib/codex-exec.mjs`) by
name as the shared executable that the `(.*/)?` optional group exists to catch, and states plainly
that "a pattern requiring an extra directory segment before `scripts/` misses that shared file
entirely" — i.e., a naive pattern like `plugins/codex-kit/.+/scripts/` (requiring something before
`scripts/`) would *fail* to match this path, which is precisely the bug step 6's phrasing is
guarding against.

The SKILL.md also explains *why* this file matters even though it isn't one of the two named
dispatch scripts (`bridge-invoke.mjs`, `guarded-dispatch.mjs`): it's "a shared executable both
dispatch scripts import and run." Preflight step 5 (materializing `review.md`/`refute.md` from
`$BASE`) protects the two *prompt* files against a self-modifying diff, but step 6 notes plainly
that "it does nothing for the *executable*" — the dispatch scripts (and the shared
`codex-exec.mjs` they both import) "are run from the working tree by a repo-relative path with no
`$BASE` verification of their own." So a diff that modifies `codex-exec.mjs` is exactly the kind of
gap step 6 exists to surface.

## What happens if it matches

Per the same step 6 paragraph and cross-referenced later in the skill:

1. **Disclosure at First-Send Confirmation** — "If any match is found, disclose it explicitly at
   the First-Send Confirmation below (not just a silent proceed)." The First-Send Confirmation
   section (lines 191–204) makes this concrete: item (c) of that mandatory `AskUserQuestion` states
   "if Preflight step 6 found the diff touching the Codex dispatcher scripts themselves, say so
   explicitly — the dispatcher about to run was not trust-boundary-verified against `$BASE` this
   run." This confirmation fires once per session, before the *first* real Codex dispatch is
   attempted, and covers both possible dispatch outcomes (sandboxed Step 1 or `danger-full-access`
   Step 2 fallback) — it is not skipped just because the sandboxed path might be used.
2. **Recorded in Phase 3's `inspection_limits`** — step 6 also requires recording "that the Codex
   dispatcher itself was not trust-boundary-verified against `$BASE` for this run." Phase 3
   (Synthesize and report) explicitly lists this as one of the `inspection_limits` items to note in
   the final report: "Preflight step 6's dispatcher-not-verified disclosure if the diff touched the
   Codex scripts themselves."
3. **No blocking, no dispatch prevention** — nothing in step 6 or the First-Send Confirmation stops
   the Codex dispatch from proceeding; the mechanism is disclosure, not a hard gate. The run
   continues (subject to the user's answer at the First-Send Confirmation — "Send to Codex for this
   run" / "Stay Claude-native for this run" — which is a general per-session gate for any first
   Codex dispatch, not one added specifically because of step 6's finding).

This exact scenario is also codified as scenario 6 in the "Testing & Validation" section (lines
370–372): "The diff itself modifies a file under `plugins/codex-kit/**/scripts/**` → Preflight step
6 finds it, the First-Send Confirmation discloses it, and Phase 3's `inspection_limits` records that
the dispatcher itself wasn't trust-boundary-verified against `$BASE`" — and as a Quality Gate bullet
(lines 378–380): "The First-Send Confirmation always fires before the *first* real Codex dispatch,
and always discloses the possible `danger-full-access` outcome and any Preflight step 6 dispatcher-
trust gap, not just the sandboxed-vs-not distinction."

## Summary

| Question | Answer |
|---|---|
| Does step 6 detect this file? | Yes |
| Pattern used | `plugins/codex-kit/(.*/)?scripts/` grepped against the Preflight step 2 changed-file list |
| Does it match `plugins/codex-kit/scripts/lib/codex-exec.mjs`? | Yes — the optional `(.*/)?` group matches zero segments, so `plugins/codex-kit/` is directly followed by `scripts/`, exactly as required; this file is the skill's own named example for why the group must be optional |
| Effect if matched | (1) Disclosed explicitly at the mandatory First-Send Confirmation (item c) before the first real Codex dispatch; (2) recorded in Phase 3's `inspection_limits` as "dispatcher itself was not trust-boundary-verified against `$BASE`"; (3) does not block or prevent the dispatch — it's a disclosure obligation, not a hard stop |
