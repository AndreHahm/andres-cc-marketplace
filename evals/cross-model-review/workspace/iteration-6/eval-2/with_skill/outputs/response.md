# Does Preflight step 6 detect a diff touching `plugins/codex-kit/skills/codex-windows-guardrails/assets/dangerous-command-instructions.txt`?

**Yes.** Preflight step 6 is specifically designed to catch this file, and the SKILL.md text names this
exact path as the reason the check is written the way it is.

## The check itself (SKILL.md lines 166–191)

Step 6 says:

> **Check whether the diff itself touches the Codex dispatcher scripts (or their non-script trust
> inputs) this skill is about to execute** — `grep -E` ... for `plugins/codex-kit/(.*/)?(scripts|assets)/`
> against the **unscoped** changed-file list (`git diff --name-only "$MERGE_BASE"`, deliberately without
> `-- "$SCOPE"`), never Preflight step 2's `$SCOPE`-filtered list.

Two things make this a whole-diff, whole-tree check rather than a narrow `scripts/`-only check:

1. **The regex pattern explicitly includes `assets/` as an alternative to `scripts/`**: `plugins/codex-kit/(.*/)?(scripts|assets)/`. The `(scripts|assets)` alternation is the operative part of the question — it is not scripts-only.
2. **The `(.*/)?` group** allows any number of intermediate path segments between `plugins/codex-kit/` and the `scripts|assets` segment, so the match isn't tied to a fixed directory depth.

Walking the target path against the pattern:

```
plugins/codex-kit/skills/codex-windows-guardrails/assets/dangerous-command-instructions.txt
plugins/codex-kit/        <- literal prefix
(.*/)?  = skills/codex-windows-guardrails/   <- optional intermediate segment(s), matched
(scripts|assets)/  = assets/                 <- matches the "assets" alternative
```

The full literal prefix `plugins/codex-kit/(.*/)?(scripts|assets)/` matches
`plugins/codex-kit/skills/codex-windows-guardrails/assets/`, so `grep -E` against the unscoped
`git diff --name-only "$MERGE_BASE"` output returns this file as a hit. Step 6 is explicit that this
must be run with `grep -E` (extended regex), not plain `grep`, because plain `grep`'s basic mode would
treat the parentheses and `?` as literal characters and silently fail to match — the SKILL.md even
documents having verified this distinction (plain `grep` exits 1 against a comparable path, `grep -E`
exits 0).

## Why the SKILL.md calls this file out by name

The skill doesn't just happen to catch this path incidentally — it names it directly as the
justification for including `assets/` in the pattern at all:

> The `assets/` alternative matters too: `guarded-dispatch.mjs` reads
> `plugins/codex-kit/skills/codex-windows-guardrails/assets/dangerous-command-instructions.txt` and
> that skill's own `assets/settings.json` (controlling whether the Windows fallback is enabled at all)
> to shape and gate a `danger-full-access` run — both live under `assets/`, not `scripts/`, so a
> `scripts/`-only pattern would miss a diff that weakens either one.

So this exact file (`dangerous-command-instructions.txt`) is one of the two concrete examples the
skill uses to explain *why* the check can't be scripts-only. The other named example is
`codex-windows-guardrails`'s own `assets/settings.json`, which gates whether the Windows
`danger-full-access` fallback path is even enabled.

## Why this file matters

`dangerous-command-instructions.txt` is a **non-script trust input** consumed by
`guarded-dispatch.mjs` (the Step-2 fallback resolver path used when the sandboxed
`codex-review-bridge` path is unavailable — e.g. local Windows, per the resolver section, lines
220–224). That fallback runs Codex with `danger-full-access` — "no sandbox at all, read *and*
write/execute" (First-Send Confirmation, line 249–250) — and this text file is one of the inputs used
to "shape and gate" that unsandboxed run. If a diff under review modified this file, it would be
altering the very safety/behavior content that governs how Codex's most dangerous execution mode
operates, in the same run that is about to dispatch Codex against that diff. Step 6 exists precisely to
flag that self-referential risk: per lines 184–187, "Step 5 protects the two *prompt* files against a
self-modifying diff; it does nothing for the *executable* or these policy inputs —
`bridge-invoke.mjs`/`guarded-dispatch.mjs` (and everything both read at runtime) are run from the
working tree by a repo-relative path with no `$BASE` verification of their own."

## What happens once the match is found

Per the closing sentence of step 6 (lines 188–191): if any match is found (as it is here), the skill
must:

1. **Disclose it explicitly at the First-Send Confirmation** (the mandatory `AskUserQuestion` gate
   before the first real Codex dispatch, lines 245–258) — "if Preflight step 6 found the diff touching
   the Codex dispatcher scripts themselves, say so explicitly — the dispatcher about to run was not
   trust-boundary-verified against `$BASE` this run." This is not a silent proceed.
2. **Record it in Phase 3's `inspection_limits`** — "the Codex dispatcher itself was not
   trust-boundary-verified against `$BASE` for this run" (step 6's closing note, and reiterated in
   Phase 3's synthesis instructions at lines 412–416, which list "Preflight step 6's
   dispatcher-not-verified disclosure if the diff touched the Codex scripts themselves" as one of the
   `inspection_limits` items to surface in the final report).

## Why the unscoped list matters here too

Step 6 deliberately greps the **unscoped** changed-file list rather than the `$SCOPE`-filtered one from
Preflight step 2: "This check asks whether the *diff as a whole* modifies the dispatcher about to run —
a property of the whole diff, not of the narrower review scope. If `$SCOPE` excludes
`plugins/codex-kit` (e.g. `$SCOPE=plugins/git-kit`), step 2's own list would silently omit a dispatcher
change made elsewhere in the same diff, defeating this check entirely on any scoped run." So even a
review deliberately scoped away from `plugins/codex-kit` would still catch a change to this file,
because step 6 always checks the full diff regardless of `$SCOPE`.

## Summary

Yes — Preflight step 6 detects this file. The regex `plugins/codex-kit/(.*/)?(scripts|assets)/`
matches it via the `assets/` alternative and the `(.*/)?` group spanning the
`skills/codex-windows-guardrails/` intermediate segment. The SKILL.md text names this precise file as
one of the two motivating examples for including `assets/` in the pattern, because it's a non-script
"policy input" (alongside `codex-windows-guardrails/assets/settings.json`) that `guarded-dispatch.mjs`
reads to shape and gate its unsandboxed `danger-full-access` Codex runs — exactly the kind of
self-referential trust-boundary risk (a diff modifying the very file that governs how Codex is
dispatched against that same diff) that step 6 exists to surface via mandatory disclosure at the
First-Send Confirmation and recording in Phase 3's `inspection_limits`.
