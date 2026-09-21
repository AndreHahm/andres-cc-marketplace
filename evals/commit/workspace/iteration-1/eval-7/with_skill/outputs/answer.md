# DRY RUN — `commit --push --bypass-codex-review "scripts/ fix"` on a brand-new branch, no PR yet

No git/gh/jq commands are actually executed below — this is a narration of what the `commit` skill's
Instructions (steps 1–18) would do with this exact invocation, given the stated facts: the push succeeds,
step 16.5 correctly defers to step 17 (no PR exists yet to attest against), step 17 finds `push_auto_pr`
is `false` and asks the user whether to create a PR now, and the user answers **no**.

## Relevant flag parsing

- `--push`: explicit override — push happens after a successful commit regardless of `commit_auto_push`.
- `--bypass-codex-review "scripts/ fix"`: reason is non-empty ("scripts/ fix"), so the flag is honored,
  not silently ignored. Per the Flags table, this flag is handled independently of the commit-message
  parsing and its reason text only ever flows through `jq -n --arg`, never a raw shell string.

Steps 1–15 (settings resolution, branch check, pre-commit checks, staging, sensitive-file scan,
Python lint, marketplace-CI parity, diff review, test-behavior-change check, multiple-concerns check,
message drafting, commitlint check, confirm-and-commit) all proceed normally and are not the focus of
this walkthrough — the task specifies the commit succeeds and we're picking up at the push/bypass/Auto-PR
sequence.

## Step 16 — Push

Not a nested `create-pr` invocation, so this step runs fully. `--push` was given, so the push happens
without asking. Since this is a brand-new branch with no upstream yet, the push is reported as
`git push -u origin HEAD` (never a branch name typed into the command — always the `HEAD` literal per
step 16's injection-safety requirement). The push succeeds.

## Step 16.5 — Bypass attestation for an already-open PR (deferred)

This step fires because `--bypass-codex-review "scripts/ fix"` was given AND step 16 actually pushed.

- (a) Reason is non-empty ("scripts/ fix") — proceed, don't skip.
- (b) Check whether a PR is already open for the current branch (`gh pr view --json number,url,headRefOid,labels`).
  **None exists** — this is a brand-new branch with no PR open yet, exactly as the scenario states.
  Per the skill's own instruction, this step does **not** attest against nothing. Instead it:
  - States plainly, in this run's output, that the bypass flag will be forwarded to step 17's Auto-PR
    flow if a PR ends up getting created there.
  - Continues to step 17 without attesting in this step.
- (c)–(g) never execute — the step exits at (b).

So at this point in the run, nothing has been posted to GitHub yet (no comment, no label) — the bypass
request is only "pending," carried forward as deferred state into step 17.

## Step 17 — Auto-PR

Not a nested `create-pr` invocation, so this step runs. After the successful push, check `gh pr view --json number`
for the current branch — still no PR open (consistent with step 16.5(b)'s finding a moment earlier).

`push_auto_pr` is `false` (per the scenario), so the skill does **not** invoke `Skill(git-kit:create-pr)`
directly. Instead it asks via `AskUserQuestion` whether to create a PR now.

**The user answers no.**

Because the user declined:
- `Skill(git-kit:create-pr)` is never invoked this run.
- The step's own explicit instruction fires: *"If this step's own 'PR already open, skip this step
  entirely' branch fires instead, or the user declines to create one, state plainly that the deferred
  bypass request had no effect this run — never silently drop it."* The "user declines" branch is exactly
  what happened here, so this disclosure is mandatory, not optional.
- No attestation comment, no `s: codex review bypassed` label, no `create-pr`-owned bypass handling ever
  happens — the deferred `--bypass-codex-review "scripts/ fix"` request simply expires unused for this run.

## Step 18 — Show the result

The final result report always includes: commit hash, files changed, insertions/deletions, and push
status (since a push did happen here). On top of that baseline content, because this run carried a
deferred, never-forwarded bypass request, the report must explicitly surface its final disposition —
per step 17's own wording and the repo's `disclose-before-overriding-decisions` rule ("never silently
skip a workflow phase" / never silently drop a pending request).

**What the final result report says about `--bypass-codex-review`, concretely:**

> Commit `<hash>` created and pushed to `<branch>` (`-u origin HEAD`, new upstream set).
> Files changed: `<N>`, insertions `<+M>`, deletions `<-K>`.
>
> **Codex-review bypass: not attested.** `--bypass-codex-review "scripts/ fix"` was deferred at step 16.5
> because no PR was open yet for this branch. It was forwarded to the Auto-PR step, but you chose not to
> create a PR this run, so **the deferred bypass request had no effect** — no bypass comment was posted
> and no `s: codex review bypassed` label was applied. If you open a PR later, re-run
> `commit --bypass-codex-review "scripts/ fix"` (or pass `--bypass-codex-review` to `create-pr` directly)
> to attest the bypass against that PR's actual head commit.

Key points the report is required to convey (traceable directly to the skill text):

1. The bypass was **never attested** — no GitHub side effects (comment/label) occurred at any point in
   this run.
2. It was **deferred, not rejected outright** — the reason text itself was valid (non-empty, no
   bot-trigger-mention problem was even reached, since (c) never ran) and remained eligible to be
   forwarded.
3. It was **forwarded to step 17 as designed**, and would have been passed through verbatim to
   `Skill(git-kit:create-pr)`'s own step 5 attestation handling had the user said yes.
4. Because the user said **no**, the request's disposition is **"had no effect this run"** — stated
   plainly, per step 17's explicit requirement, not silently dropped.
5. The report gives the user a concrete next action (re-invoke with the same flag once a PR exists) rather
   than leaving the outcome ambiguous.

This is the same "never report a failed attestation as if it succeeded" discipline step 16.5(g) states
for its own success/failure branch, applied here to the deferred-and-then-unused case: the report is
explicit that the bypass did **not** happen, why, and what would need to happen for it to take effect.
