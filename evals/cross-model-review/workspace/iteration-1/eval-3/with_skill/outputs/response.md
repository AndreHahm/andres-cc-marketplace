# Where this matters, and why

The scenario described — a diff that is itself about to be reviewed by `cross-model-review`, and
that diff modifies `plugins/git-kit/skills/cross-model-review/prompts/review.md` (adding a line to
the fresh-eyes persona) — lands squarely on **Preflight step 5**, "Materialize trusted reviewer
instructions from `$BASE` — never the working tree."

This is the one Preflight step that exists specifically for this situation. The skill's own stated
concern is: "The working tree may *be* the branch under review; loading judging instructions from it
would let a reviewed diff rewrite the rules that judge it." That is exactly what's happening here —
the diff under review isn't just touching unrelated application code, it's touching the very file
(`review.md`) that defines what "fresh-eyes persona" instructions get handed to both Claude and
Codex in Phase 1. If Preflight simply read `review.md` from the working tree (HEAD of the branch
being reviewed), the added line would already be in effect for judging the very diff that added it —
a diff could, in principle, use this to soften or redirect its own review criteria, and no one would
catch it because the "rules" and the "thing being judged by the rules" would be the same commit.

Preflight step 5 closes that hole by never trusting the working tree for this file. It sources
`review.md` from `$BASE` (default `main`) instead — a ref the diff hasn't touched, since `$BASE` is
the pre-diff reference point the whole review is diffing against.

# The exact command that resolves it

```bash
git show "$BASE:plugins/git-kit/skills/cross-model-review/prompts/review.md" > "$RUN/review.md" 2>/dev/null \
  || { cp "${CLAUDE_PLUGIN_ROOT}/prompts/review.md" "$RUN/review.md"; REVIEW_UNVERIFIED=1; }
```

Walking through it:

- `git show "$BASE:plugins/git-kit/skills/cross-model-review/prompts/review.md"` asks git for the
  blob content of that exact path *as it existed at the tip of `$BASE`* — not the working tree, not
  HEAD of the branch under review, not an index/staged version. Since `$BASE` is what the diff is
  computed against (`git diff "$BASE...HEAD"`), and the diff in this scenario modifies `review.md`,
  the content `git show` returns here is the **pre-change** version of the file — the one without
  the new fresh-eyes-persona line the PR is adding.
- That output is redirected into `$RUN/review.md`, the scratch copy that every later reference to
  "`review.md`" in the skill (Phase 1's Claude native pass, and the file that gets copied into
  `review_for_codex.md` for Codex's dispatch) actually reads from. The skill is explicit that after
  this step, "every later reference to `review.md` / `refute.md` below means these materialized
  `$RUN` copies, never the live path under `${CLAUDE_PLUGIN_ROOT}`."
- Net effect for this specific diff: both Claude and Codex review the diff (which includes the new
  line being added to `review.md`) **using the old, pre-PR fresh-eyes instructions** — the new line
  itself has no effect on how this review run is judged, by design. That's the trust boundary working
  as intended.
- `2>/dev/null` suppresses git's stderr if the lookup fails, and `||` chains the fallback so a failed
  `git show` doesn't abort Preflight.

# What happens if `git show` fails (file doesn't exist on `$BASE` yet)

The skill names this exact case explicitly: "A `git show` failure means the file doesn't exist on
`$BASE` yet (e.g. this skill's own not-yet-merged first run)." That matches a first-commit /
not-yet-merged bootstrap scenario — `prompts/review.md` (the whole `cross-model-review` skill, in
its very first run) simply isn't present in `$BASE`'s tree at all, so `git show $BASE:<path>` exits
non-zero and prints its "path does not exist" error to stderr (swallowed by `2>/dev/null`).

When that happens, the `||` fallback fires:

```bash
cp "${CLAUDE_PLUGIN_ROOT}/prompts/review.md" "$RUN/review.md"; REVIEW_UNVERIFIED=1
```

- It falls back to copying `review.md` from `${CLAUDE_PLUGIN_ROOT}` — i.e. the **live, working-tree
  copy** of the file, the exact thing step 5 was designed to avoid trusting. In the scenario given
  (the diff adds a line to this same file), that live copy is the *new* version, including the added
  line — so in this specific failure path, the trust-boundary protection is not actually available;
  the skill degrades to using the very content the diff is changing.
- `REVIEW_UNVERIFIED=1` is set as a flag. This is not a fatal error — Preflight does not stop the
  run. The skill's instructions are explicit that this must never happen silently: "fall back to the
  working-tree copy, but never silently: record it in Phase 3's `inspection_limits`."
- Downstream consequence: Phase 3 (Synthesize and report) must note in its `inspection_limits`
  output that "reviewer instructions were not trust-boundary-verified against `$BASE` this run" (the
  skill gives this near-verbatim as the wording to use), triggered by `REVIEW_UNVERIFIED` — or,
  symmetrically, `REFUTE_UNVERIFIED` if the analogous `git show` for `refute.md` also failed. This
  keeps the limitation visible to whoever reads the final report rather than letting the run look
  like a normal, fully trust-boundary-verified pass.

# Summary of the mechanics for this exact diff

1. Preflight step 5 runs before Phase 1, specifically to source `review.md`/`refute.md` from a
   ref the diff cannot have touched.
2. `git show "$BASE:...review.md"` is attempted first. If `$BASE` already has some (older) version of
   the file — the normal case for a diff that merely *modifies* an existing, already-merged file —
   this succeeds and returns the pre-diff content, so the new line being added has no bearing on how
   this run's own review is conducted.
3. If that lookup fails — the file/skill doesn't exist on `$BASE` at all (first, not-yet-merged
   commit) — the command falls back to copying the working-tree copy from `${CLAUDE_PLUGIN_ROOT}`
   instead, sets `REVIEW_UNVERIFIED=1`, and continues rather than aborting.
4. That flag must surface later, in Phase 3's `inspection_limits`, as an explicit disclosure that this
   run's reviewer instructions were not verified against `$BASE` — never silently absorbed.
