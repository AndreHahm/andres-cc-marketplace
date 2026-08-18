# Does `git add -N` abort Preflight when SCOPE resolves only to a deleted tracked file?

**Short answer: No — the skill handles this gracefully by design, and the deletion is still reported
correctly.** The skill's Inputs section explicitly anticipates exactly this scenario and neutralizes it
with a deliberate `|| true`, and confirms the deletion still shows up in the diff regardless of whether
the intent-add step succeeded.

## What the skill actually does

The relevant code is in the **Inputs** section (SKILL.md lines 95–104):

```bash
BASE="${BASE:-main}"
MERGE_BASE=$(git merge-base "$BASE" HEAD)
UNTRACKED_FILES=$(git ls-files --others --exclude-standard -- "${SCOPE:-.}")
export GIT_INDEX_FILE="$(mktemp -u)"
git add -N -- "${SCOPE:-.}" || true
DIFF=(git diff "$MERGE_BASE")
[ -n "$SCOPE" ] && DIFF+=(-- "$SCOPE")   # [ ... ] invokes the test command; matches the Bash(test:*) grant
DIFF_STR=$(printf '%q ' "${DIFF[@]}")   # shell-quoted rendering, for embedding in a prompt
```

The `git add -N -- "${SCOPE:-.}"` call is followed by `|| true`. The skill spells out exactly why,
immediately below this block:

> **"The `|| true` here matters when `$SCOPE` names only a deletion"** — `git add -N` needs its pathspec
> to match something on disk, so a `$SCOPE` resolving only to a deleted tracked file fails outright
> (`fatal: pathspec ... did not match any files`) and, untolerated, aborts the whole `&&`-chained
> Preflight before `git diff` runs. Verified: the unscoped default never hits this. `git diff
> "$MERGE_BASE" -- "$SCOPE"` still shows the deletion regardless of whether the intent-add succeeded.
> (lines 106–110)

So for the case in the question — SCOPE is a pathspec that resolves *only* to a file that existed at
`$BASE` and was removed in this diff, with nothing else under that path changed — `git add -N` has
nothing on disk to match (the file no longer exists in the working tree), and it exits non-zero with
`fatal: pathspec ... did not match any files`. Without the `|| true`, this would kill the whole chained
`&&` Preflight sequence (the Preflight section, lines 125–132, explicitly runs steps 1–6 "as a single
chained Bash invocation (`&&` between them, one tool call)", so any single non-tolerated failure in that
chain would abort everything downstream — the `$RUN` dir, `$REPO_ROOT`, the materialized reviewer
instructions, etc.). The `|| true` swallows that specific failure so the chain proceeds to the next
statement, `DIFF=(git diff "$MERGE_BASE")` / the scoped diff build.

This is the same pattern the skill uses elsewhere for an *expected* failure that must not break the
chain — see Preflight step 5's own `git show ... || true` calls with the parallel comment: **"The `||
true` on each line is deliberate — an expected `git show` failure must not break the `&&` chain the
whole Preflight sequence runs as, or every resolved value this skill depends on for the rest of the run
is lost with it."** (lines 193–195). The `git add -N` case is the same design decision applied earlier
in the same chain.

## Does the deletion still get reported correctly?

Yes. Two independent reasons, both stated in the skill:

1. **`git diff` doesn't need intent-to-add for a deletion in the first place.** The intent-to-add
   (`git add -N`) mechanism exists specifically to make a *brand-new untracked file* visible to `git
   diff` — the Inputs section's preceding paragraph explains this is needed because "a brand-new file
   that was never `git add`ed shows up in `git status` as `??` but produces *no* output from `git diff`
   ... until `git add -N` ... records it" (lines 77–84). A deletion of a file that was already tracked
   at `$BASE` is a completely different case: it's already present in the merge-base tree, so `git diff
   "$MERGE_BASE" -- "$SCOPE"` sees and reports it as a deletion regardless of whether `git add -N`
   succeeded, failed, or was even attempted. The skill states this outcome explicitly in the same
   sentence quoted above: *"`git diff "$MERGE_BASE" -- "$SCOPE"` still shows the deletion regardless of
   whether the intent-add succeeded"* (line 110).
2. **Preflight step 1 treats this as a normal, successful diff, not an empty-scope condition.** Step 1
   (lines 134–138) runs `"${DIFF[@]}"` and checks its exit status: *"A non-zero exit ... is a Preflight
   failure ... Only a successful command (exit 0) with empty stdout means the diff is genuinely empty."*
   A deletion-only diff for the scoped file exits 0 with non-empty stdout (the deletion patch), so it is
   neither treated as a Git error nor as "nothing to review" — it proceeds normally into Claude's native
   Phase 1 review, which already has the full diff (including the deletion) in context.

## One downstream consequence worth noting: Codex gets skipped, not the whole review

Although Preflight itself does not abort, this specific scenario does trigger a different, intentional
branch later in Preflight — the Codex-eligibility check in **step 2** (lines 139–178):

> `codex-review-bridge` validates each target path against `^[A-Za-z0-9._/-]+$` and
> `codex-windows-guardrails` additionally requires the path to still exist on disk — a path containing
> any other character, or a path the diff *deletes*, cannot go through either dispatch as-is. If any
> changed path fails that pattern or no longer exists, exclude it from `--target-paths` ...

Since SCOPE names *only* the one deleted file, this is also the file's *only* entry in the changed-file
list for `--target-paths`, so after exclusion the eligible-files list is empty. Step 2 explicitly
handles this too:

> **"If the eligible-files list is empty after exclusions (every changed file was deleted or had an
> invalid character), skip Codex entirely and enter single-model mode now — before attempting any
> dispatch."** ... record the `inspection_limits` reason as "zero Codex-eligible paths in this diff"
> rather than "Codex unavailable" (lines 171–178)

So the practical end-to-end outcome for this run is:

- Preflight completes successfully (no abort) — the `git add -N || true` tolerance plus `git diff`'s
  native ability to show deletions without intent-to-add together guarantee this.
- Claude's native Phase 1 review runs normally against the full diff and correctly reports the deletion.
- Phase 1's Codex pass and all of Phase 2 are skipped (single-model mode), per resolver step 3's
  single-model path and Phase 3's single-model handling (lines 418–425): every finding is capped at
  Medium confidence, and `inspection_limits` records `single_model_mode: true` with the reason "zero
  Codex-eligible paths in this diff" — not "Codex unavailable," since Codex was never actually attempted
  here.
- The final report still surfaces the deletion (and any finding about it) — just as a single-model,
  Medium-confidence result rather than a cross-examined one, exactly as Phase 3's single-model note and
  the Medium tier bullet (lines 445–452) describe.

## Summary

| Question | Answer | Citation |
|---|---|---|
| Does `git add -N` abort the whole Preflight chain? | No — `\|\| true` on that exact line is a deliberate tolerance for precisely this case. | Inputs section, lines 100 and 106–110 |
| Would it fail without the `\|\| true`? | Yes — `git add -N` needs a pathspec match on disk; a deletion-only SCOPE has none, so it would exit non-zero (`fatal: pathspec ... did not match any files`) and break the `&&` chain. | lines 106–108 |
| Does the deletion still get reported? | Yes — `git diff` shows tracked-file deletions natively; intent-to-add is only needed for untracked *additions*, not deletions. | lines 77–84, 110 |
| Does Preflight step 1 treat this as "nothing to review"? | No — exit 0 with non-empty stdout (the deletion patch) is a normal successful diff, not the empty-scope case. | lines 134–138 |
| Any other effect of this scenario? | Yes — the deleted path fails Codex's on-disk-existence/target-path validity check, so after exclusion the eligible-files list is empty and the run enters single-model mode (Codex skipped entirely), with `inspection_limits` recording "zero Codex-eligible paths in this diff." | lines 139–178, 418–425 |
