DRY RUN — narrated walkthrough only. No Bash/git/gh/Skill/Agent tool calls were actually made.

Starting point (all parts): branch `feat/example-widget`, everything committed and pushed, no PR
open, no issue mentioned. Skill in use: `create-pr`.

================================================================================
PART A — "create a PR for this." (no flags)
================================================================================

Pre-flight Checks:

1. Run `git status`. Nothing to see here — everything is already committed and pushed, so the
   working tree is clean.
2. Since there are no uncommitted changes, step 2 (invoking `Skill(git-kit:commit)`) is skipped
   entirely — there's nothing to commit.
3. (Confirms all work is committed — already true.)
4. **Cross-model-review gate — mandatory unless bypassed, and no bypass flag was given here.**
   `create-pr` invokes `Skill(git-kit:cross-model-review)` against the full current diff, default
   `BASE=main`, no `SCOPE` restriction — i.e. the entire diff of `feat/example-widget` against
   `main`, not just the files touched most recently. This is a genuine independent/adversarial
   review: Claude reviews the diff natively, and Codex reviews it independently through codex-kit
   (codex-review-bridge, or codex-windows-guardrails as fallback). Both personas then
   cross-examine: a fresh-eyes pass (Phase 1, independent read) and a challenger pass (Phase 2,
   confirms/refutes/adds novel findings against the other model's output). The result is a ranked,
   confidence-scored findings table; `cross-model-review` never edits code itself.

   Inside this nested invocation, `cross-model-review`'s own mandatory First-Send Confirmation
   still fires normally — the per-invocation Codex-dispatch consent gate, including its disclosure
   that a Codex pass sends the diff's content to a third-party vendor subprocess and that the
   findings JSON persists under the OS temp directory afterward. `create-pr` does not suppress or
   pre-answer that confirmation.

   **Does the manual run from five minutes ago count?** No. The skill is explicit on this point:
   "Re-invoke it fresh here even if it was already run manually earlier in this session against
   what looks like the same diff — the diff may have changed since then, and this gate exists
   specifically to catch findings at the cheapest point in the review loop, immediately before the
   first push." So the earlier hand-run review, however recent and however similar-looking, does
   not satisfy this gate. `cross-model-review` is invoked again, fresh, treating the two runs as
   fully independent (this also matches the general repo rule of never trusting a stale
   externally-observed check for a side-effecting action — re-check immediately before acting).

Assuming this pass comes back clean (no findings, or the user declines any raised) — see Part D
for what happens when it doesn't — `git status` is re-checked (no edit was produced, so it's still
clean), and the flow proceeds straight to "Creating a New Pull Request" step 1: push (no-op, branch
already on remote and unchanged), prepare description from the resolved template, ask draft vs.
ready via `AskUserQuestion`, validate the title against the CI policy script, resolve the assignee,
write the git-kit marker, and run `gh pr create` (with `--draft` if applicable, `--assignee <login>`).
No issue was named, so the issue-linking hand-off to `collaborating-on-a-pr` is skipped.

================================================================================
PART B — --bypass-cross-model-review "already reviewed manually, low-risk docs change"
================================================================================

Pre-flight steps 1–3 are unchanged: `git status` clean, nothing to commit, work already committed.

Step 4 changes: because a non-empty reason is supplied with the flag, the mandatory
`Skill(git-kit:cross-model-review)` invocation is skipped entirely — no adversarial review runs
against this diff at all, by either model. The skill explicitly instructs reporting the bypass and
its reason plainly in this session's output.

**Is anything posted to GitHub because of this flag?** No. The skill draws this contrast directly:
"Lightweight compared to `--bypass-codex-review`: no GitHub comment, label, or permission check —
`cross-model-review` is a local, pre-push practice with no GitHub-side enforcement to attest
against. The reason is reported in this session's output only, never written to the PR body or any
GitHub-visible location." So the bypass reason stays local to this session's narration — it does
not appear in the PR description, as a PR comment, as a label, or anywhere else on GitHub.

The rest of the flow proceeds exactly as in Part A's tail: push (no-op), prepare description, ask
draft vs. ready, validate title, resolve assignee, write marker, `gh pr create`. The PR itself gets
created normally — that's the ordinary flow, not something caused by this flag — but nothing about
its content or GitHub-visible metadata differs because of the bypass.

================================================================================
PART C — --bypass-cross-model-review "" (empty reason)
================================================================================

The flag is present but its reason is empty. Per the skill: "if the flag is present with an empty
or missing reason, reject it and ask for a valid reason before proceeding; don't silently fall
through to running the gate anyway, and don't create the PR while the bypass request is still
invalid."

So concretely: `create-pr` rejects the flag as given, and asks the user for a valid (non-empty)
reason before doing anything further. Two things explicitly do NOT happen in this state:
- It does not silently run the cross-model-review gate anyway as a fallback.
- It does not create the PR while the bypass request is still invalid.

The flow is paused at this point, pending the user either supplying a real reason (after which
Part B's behavior applies) or dropping the flag entirely (after which Part A's behavior applies —
the gate runs for real). Nothing is pushed and no PR is created until that's resolved.

================================================================================
PART D — Part A's scenario, gate finds one finding, user fixes it, walk it all the way through
================================================================================

Starting from Part A: pre-flight steps 1–3 clean/no-op, step 4 fires `Skill(git-kit:cross-model-review)`
against the full diff (`BASE=main`). This first pass returns one finding. The user says: fix it.

1. **The fix is applied.** A file in the working tree is edited to address the finding. This edit
   is made as a normal edit by this session — not by `create-pr` and not by `cross-model-review`
   itself, since that skill is report-only and never edits code. The working tree is now dirty
   again; the diff has changed since the last time anything checked tree state (the step-4 gate's
   own review only ever saw the pre-fix diff).

2. **Re-invoke `Skill(git-kit:commit)`**, per the skill's explicit re-commit-then-re-review loop
   instructions, passing the same two constraints the original pre-flight step 2 would have passed
   had there been uncommitted work at that point: (a) skip `commit`'s own Auto-PR step, and (b)
   skip `commit`'s own step-16 push entirely — stage and commit only, don't even ask the
   push-confirmation question. So this step stages the fixed file and creates a local commit. **No
   push happens here** — this is explicitly, deliberately suppressed by the skill so the branch
   cannot reach the remote before the fix itself has been reviewed.

3. **Re-invoke `Skill(git-kit:cross-model-review)` again**, against the new current diff — the one
   that now includes the fix, still `BASE=main`, still full scope, before proceeding to step 1 of
   PR creation. The skill is explicit that the first pass "only reviewed the pre-fix diff, not the
   diff this run is actually about to push" — so this second invocation is not optional or
   redundant, it's the only thing that ever reviews the fix itself. Inside this second invocation,
   `cross-model-review`'s First-Send Confirmation (and its Codex-dispatch/third-party/temp-file
   disclosures) fires again — the skill notes explicitly this is not a one-time cost; every
   iteration of this loop re-triggers it.

4. **Loop condition.** If this second pass raises a newly-accepted finding, the same
   commit-then-re-review cycle repeats (edit → `Skill(git-kit:commit)`, no push →
   `Skill(git-kit:cross-model-review)` again on the newest diff) for as long as passes keep
   producing newly-accepted edits. The loop's exit is: a pass produces no newly-accepted edit
   (everything raised on that pass — new or a repeat of an earlier declined one — was declined, or
   nothing was raised at all). For this walkthrough, assume the second pass clears (nothing new
   accepted) — the loop exits after this one iteration.

5. **`git status` is re-checked** one more time per the skill's mirrored steps-1–3 logic (a status
   read from before the gate ran is treated as stale). It's clean — the fix is committed, nothing
   else pending.

6. **Only now does "Creating a New Pull Request" step 1 run: push the current branch to remote.**
   This is the first and only point in this entire scenario where anything reaches the remote. The
   push carries both the original already-pushed history and the new local fix commit made in step
   2 above.

7. From there, the rest of the flow proceeds normally: prepare the PR description from the
   resolved template, ask draft vs. ready-to-merge via `AskUserQuestion`, validate the PR title
   against the CI policy script, resolve the assignee via `gh api user`, write the git-kit marker,
   and run `gh pr create` (with `--draft` if applicable, `--assignee <login>`). No issue was named,
   so no hand-off to `collaborating-on-a-pr`.

**Direct answers to the two specific questions posed:**

- **Does the re-committed fix itself ever get pushed anywhere before anything else happens to it?**
  No. The fix is committed locally in step 2 and deliberately not pushed at that point (`commit`'s
  step 16 push is explicitly skipped by instruction). The very next thing that happens to it is
  being reviewed again by the second `cross-model-review` pass (step 3) — only after that pass
  clears does the branch, fix included, get pushed in step 6.

- **Does anything look at the new diff (with the fix in it) before the branch is pushed, or does
  only the original pre-fix diff ever get reviewed?** The new diff, fix included, is reviewed —
  by the second `cross-model-review` invocation in step 3 — and this happens strictly before the
  push in step 6. The original pre-fix diff is not the only thing ever reviewed; it's specifically
  the fact that the first pass's clearance doesn't count for the post-fix diff that forces the
  second pass to exist at all, per the skill's own reasoning ("a `git status` read taken before
  this gate ran is stale once the gate has had a chance to change the working tree").
