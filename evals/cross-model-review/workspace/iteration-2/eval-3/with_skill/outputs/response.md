# Where this matters, step by step

## 1. It is a Preflight step 5 concern, not step 6

The diff in question touches `plugins/git-kit/skills/cross-model-review/prompts/review.md` — one of
the two *reviewer instruction prompts*. That's Preflight **step 5** ("Materialize trusted reviewer
instructions from `$BASE` — never the working tree"), not step 6. Step 6 only greps the changed-file
list for `plugins/codex-kit/.*/scripts/.*` (the Codex *dispatcher* scripts, `bridge-invoke.mjs` /
`guarded-dispatch.mjs`). A change under `plugins/git-kit/skills/cross-model-review/prompts/` doesn't
match that pattern, so step 6 doesn't fire for this diff — it's a different trust-boundary concern
(dispatcher-not-verified vs. instructions-not-verified) with its own separate disclosure. Worth being
explicit about this because the two steps look similar (both are "don't trust the working tree") but
guard different assets and populate different `inspection_limits` entries.

Step 2 (target-paths validation for Codex dispatch) is also worth a quick pass-through check here: the
path `plugins/git-kit/skills/cross-model-review/prompts/review.md` matches
`^[A-Za-z0-9._/-]+$` cleanly (only letters, digits, `.`, `/`, `-`) and the file still exists on disk (it's
a modification, not a deletion), so it wouldn't be excluded from Codex's `--target-paths` on that
account. That check is orthogonal to the step-5 trust-boundary question, though — passing step 2 just
means Codex is allowed to *see* the file as a target path; it says nothing about which *content* of
`review.md` gets loaded as the reviewer's actual instructions.

## 2. The exact command that resolves it

Step 5 runs two independent `git show` calls, one per prompt file:

```bash
git show "$BASE:plugins/git-kit/skills/cross-model-review/prompts/review.md" > "$RUN/review.md" 2>/dev/null
git show "$BASE:plugins/git-kit/skills/cross-model-review/prompts/refute.md" > "$RUN/refute.md" 2>/dev/null
```

For this scenario, the one that resolves the "adds a line to the fresh-eyes persona" edit is the first
line — the `review.md` `git show`. It asks git for the **blob of `review.md` as it exists in the
`$BASE` ref's tree**, not the working tree, and writes that blob to `$RUN/review.md`. This is the
literal mechanism enforcing "never load judging instructions from the branch under review" — `$BASE`
(default `main`) is presumed not to contain the diff's own edits yet, so whatever the diff did to the
fresh-eyes persona can't be the thing that governs how the diff itself gets judged.

## 3. What happens when the command fails because the file doesn't exist on `$BASE`

This is exactly Testing scenario 5's case: "this skill's own first, not-yet-merged run." If
`plugins/git-kit/skills/cross-model-review/prompts/review.md` doesn't exist in `$BASE`'s tree at all
(e.g. the whole skill, prompts and all, was only ever added on this branch and hasn't merged to `main`
yet), `git show "$BASE:...review.md"` fails with a non-zero exit and prints an error to stderr — which
step 5's `2>/dev/null` silently discards. The `>` redirection on the left still runs regardless of the
command's exit status, so `$RUN/review.md` gets created, but as an empty (0-byte) file rather than
absent entirely.

Step 5 defines the failure condition as "a `git show` failure (non-zero exit, or an empty
`$RUN/review.md`/`$RUN/refute.md`)" — so either signal (exit code or empty output) is sufficient to
detect this case; it doesn't rely on exit code alone, which matters because `git show` behaves slightly
differently between "path not found in that ref" and "ref-and-path combination invalid" but both leave
`$RUN/review.md` empty either way.

## 4. The fallback, and what it means for *this specific* diff

On that detected failure, step 5's fallback is:

1. `Read` the working-tree copy at
   `${CLAUDE_PLUGIN_ROOT}/skills/cross-model-review/prompts/review.md` (note: `${CLAUDE_PLUGIN_ROOT}`
   resolves to the plugin root, `plugins/git-kit/`, so the full path still needs the
   `skills/cross-model-review/` segment — it is not itself the skill's directory).
2. `Write` that content to `$RUN/review.md`.
3. Set `REVIEW_UNVERIFIED=1` (checked and set independently of `REFUTE_UNVERIFIED`, since each prompt
   file's `git show` is evaluated on its own).
4. Record in Phase 3's `inspection_limits`: "reviewer instructions were not trust-boundary-verified
   against `$BASE` this run."

The pointed consequence for *this* diff specifically: the working-tree copy of `review.md` is the
**new** version — the one with the line just added to the fresh-eyes persona. Because `$BASE` has no
copy of the file to fall back from, the fallback has no choice but to pull the diff's own edited
version of the instructions that will then govern the diff's own review pass. That's precisely the
self-ratification risk step 5's opening paragraph exists to prevent ("the working tree may *be* the
branch under review; loading judging instructions from it would let a reviewed diff rewrite the rules
that judge it") — and in this one edge case (first, not-yet-merged run) it can't be avoided, only
disclosed. The skill doesn't treat that as silently acceptable: `REVIEW_UNVERIFIED=1` and the
Phase 3 `inspection_limits` line are exactly the "never silently" disclosure mechanism for this case —
the report a user reads at the end will say the fresh-eyes instructions weren't `$BASE`-verified this
run, so a reader can weigh that when judging how much to trust the findings.

Everything downstream keeps working off `$RUN/review.md` as normal — Claude's native Phase 1 pass reads
it directly, and Codex's Phase 1 pass gets it via `Read $RUN/review.md` + append `Review the diff:
$DIFF_STR` + `Write` to `$RUN/review_for_codex.md` — the fallback is transparent to every later step
except for the one disclosure flag threading through to the final report.

## 5. Scope check on `refute.md`

The task only asks about `review.md`, but it's worth noting the two `git show` calls are independent:
if `refute.md` already existed on `$BASE` before this branch (i.e., only `review.md` was edited on this
diff), its `git show` would succeed normally and `REFUTE_UNVERIFIED` would stay unset — only
`REVIEW_UNVERIFIED` fires. If this really is the skill's *first* commit and neither prompt file exists
on `$BASE` yet (matching the parenthetical in the task and Testing scenario 5 verbatim), both fallbacks
fire independently, each with its own flag, and Phase 3 reports both.

## 6. No hard stop

None of this halts the skill. Preflight step 5's fallback is graceful-degrade-with-disclosure, not a
failure path — the skill proceeds through Phases 1–3 exactly as normal, using the fallback-sourced
`$RUN/review.md`, and the only observable difference in the final report is the added
`inspection_limits` line. This matches the skill's stated Quality Gate: "Preflight step 5 always
sources reviewer instructions from `$BASE` via `git show`, never directly from
`${CLAUDE_PLUGIN_ROOT}/skills/cross-model-review/...` on the happy path — the working-tree copy is a
disclosed fallback only, not the default."
