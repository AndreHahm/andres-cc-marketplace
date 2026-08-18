# Does Preflight step 6 detect the out-of-scope `plugins/codex-kit/scripts/` change?

**Yes.** Preflight step 6 is specifically designed to catch exactly this case — a diff that touches
`plugins/codex-kit/**/scripts/**` even when `SCOPE` (here `plugins/git-kit`) would otherwise exclude
that path from the review. This is not an edge case the skill happens to handle; it's the scenario
step 6 was written for, and it is called out by name in both the skill's Preflight section and its
Testing & Validation section.

## What list step 6 checks against

Per `SKILL.md` lines 139–145 (Preflight, step 6):

> "**Check whether the diff itself touches the Codex dispatcher scripts this skill is about to
> execute** — grep for `plugins/codex-kit/(.*/)?scripts/` against the **unscoped** changed-file list
> (`git diff --name-only "$BASE...HEAD"`, deliberately without `-- "$SCOPE"`), never Preflight step
> 2's `$SCOPE`-filtered list."

So concretely:

- **List used:** `git diff --name-only "$BASE...HEAD"` — the *full, unscoped* changed-file list for
  the entire diff between `$BASE` and `HEAD`.
- **List explicitly NOT used:** Preflight step 2's list, which is
  `git diff --name-only "$BASE...HEAD" [-- "$SCOPE"]` — i.e. the same diff but filtered down to only
  the paths under `SCOPE` (`plugins/git-kit` in this run). That filtered list is what feeds
  `--target-paths` for the Codex dispatch, but it is explicitly *not* what step 6 greps against.
- **Pattern:** `plugins/codex-kit/(.*/)?scripts/` — a regex with an optional intervening directory
  group. The file in question, something under `plugins/codex-kit/scripts/`, matches this pattern
  directly (the `(.*/)?` group simply matches nothing in that case, same as it would match one or
  more directory segments for a deeper path like
  `plugins/codex-kit/skills/<name>/scripts/*.mjs`, or the shared
  `plugins/codex-kit/scripts/lib/codex-exec.mjs`).

Since the file in question — a file under `plugins/codex-kit/scripts/` — is part of the *unscoped*
`$BASE...HEAD` diff (the question states it's part of "the actual diff (unscoped)"), it will appear
in `git diff --name-only "$BASE...HEAD"` regardless of what `SCOPE` is set to, and the grep against
that pattern will match it. Step 6 will therefore detect it even though `SCOPE=plugins/git-kit` would
have caused Preflight step 2's own (differently-purposed) list to omit it entirely.

## Why step 6 deliberately uses the unscoped list

The skill states the rationale directly, line 143–145:

> "This check asks whether the *diff as a whole* modifies the dispatcher about to run — a property of
> the whole diff, not of the narrower review scope. If `$SCOPE` excludes `plugins/codex-kit` (e.g.
> `$SCOPE=plugins/git-kit`), step 2's own list would silently omit a dispatcher change made elsewhere
> in the same diff, defeating this check entirely on any scoped run."

The reasoning connects to two other parts of the skill:

1. **What the check protects against.** Step 6's own text (lines 149–155) explains that Preflight
   step 5 already protects the two *prompt* files (`review.md`/`refute.md`) from a self-modifying
   diff by loading them from `$BASE` via `git show`, never the working tree. But nothing protects the
   *executable* dispatcher scripts (`bridge-invoke.mjs`, `guarded-dispatch.mjs`, and the shared
   `codex-exec.mjs` they both import) — those are "run from the working tree by a repo-relative path
   with no `$BASE` verification of their own." Since this skill is about to `node`-execute those
   exact scripts later (see the "Codex dispatch resolver" section), a diff that modifies them is a
   trust-boundary risk: the code about to run to judge the diff could itself have been altered by
   that same diff. That risk exists at the level of "does the whole diff touch the dispatcher,"
   independent of whatever narrower slice the user asked to have *reviewed*.

2. **Why using the SCOPE-filtered list would silently defeat the check.** `SCOPE` narrows what gets
   *reviewed* (which files get sent to the reviewers, what appears in `--target-paths`, what's in
   `$CODEX_DIFF_STR`) — but it says nothing about what the rest of the diff, outside that scope,
   might have changed. If step 6 grepped Preflight step 2's `$SCOPE`-filtered list instead, then any
   run where `SCOPE` excludes `plugins/codex-kit` would never see the dispatcher-script path at all,
   even if that path really is part of the same commit range being reviewed — silently defeating the
   entire safety check on exactly the runs (scoped ones) where a user is least likely to be looking at
   that part of the diff themselves.

## Downstream consequences once step 6 fires

Confirmed by the skill's own Testing & Validation scenario 6 (lines 398–402), which is essentially
this exact question restated as a test case:

> "The diff itself modifies a file under `plugins/codex-kit/**/scripts/**`, **including when `$SCOPE`
> is set to exclude that path from the review** → Preflight step 6 still finds it (it checks the
> unscoped `$BASE...HEAD` diff, independent of `$SCOPE`), the First-Send Confirmation discloses it,
> and Phase 3's `inspection_limits` records that the dispatcher itself wasn't trust-boundary-verified
> against `$BASE`."

Concretely, once step 6 matches:

- It must be **disclosed explicitly at the First-Send Confirmation** (line 152–155, and reiterated in
  the First-Send Confirmation section, lines 199–207, item (c)): "if Preflight step 6 found the diff
  touching the Codex dispatcher scripts themselves, say so explicitly — the dispatcher about to run
  was not trust-boundary-verified against `$BASE` this run." This must happen *before* the backend is
  resolved / before the first real Codex dispatch, not folded silently into the final report.
- It must be **recorded in Phase 3's `inspection_limits`** (line 152–155 again, and Phase 3's own
  listing at lines 341–344): "Preflight step 6's dispatcher-not-verified disclosure if the diff
  touched the Codex scripts themselves."
- This is also captured as one of the skill's own **Quality gates** (lines 413–415 and 427–428):
  the First-Send Confirmation "always... discloses... any Preflight step 6 dispatcher-trust gap, not
  just the sandboxed-vs-not distinction," and "Preflight step 6's dispatcher-trust check always uses
  the unscoped `$BASE...HEAD` diff — never Preflight step 2's `$SCOPE`-filtered changed-file list."

## Summary

- Step 6 checks the **unscoped** `git diff --name-only "$BASE...HEAD"` list (full diff, no `-- "$SCOPE"` filter), explicitly *not* Preflight step 2's `$SCOPE`-filtered list.
- It greps that list for `plugins/codex-kit/(.*/)?scripts/`, a pattern that matches both nested skill-owned dispatcher scripts and the shared `codex-exec.mjs`.
- Because the changed file under `plugins/codex-kit/scripts/` is part of the unscoped diff regardless of `SCOPE=plugins/git-kit`, step 6 will find it on this run.
- The reason for checking the unscoped list is that the dispatcher-trust question ("did this diff modify the code about to be executed to review it?") is a property of the whole diff, not of the narrower slice the user chose to have reviewed — using the SCOPE-filtered list would silently blind the check on precisely the runs where SCOPE excludes `codex-kit`.
- Once matched, the finding must be disclosed at the First-Send Confirmation (before any real Codex dispatch) and recorded in Phase 3's `inspection_limits`, per the skill's own Preflight step 6 text, First-Send Confirmation section, Phase 3 section, Testing scenario 6, and Quality gates checklist.
