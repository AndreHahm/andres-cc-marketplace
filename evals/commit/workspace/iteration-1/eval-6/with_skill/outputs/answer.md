# DRY RUN — `commit --push --bypass-codex-review "urgent fix"` (already-open PR, insufficient permission)

**No git/gh/jq commands are actually executed below.** This is a narrated walk-through of what the
`commit` skill (git-kit) does next, per its SKILL.md, given:

- Invocation: `commit --push --bypass-codex-review "urgent fix"`
- Current branch already has an open PR.
- Step 16 (**Push**) has already run and succeeded (`git push origin HEAD`).
- At step 16.5(d), `gh api repos/{owner}/{repo}/collaborators/{actor}/permission --jq '.permission'`
  returns `read` for the current actor.

Steps 1–15 (settings resolution, trust check, branch check, lint, staging, sensitive-file scan, Python
lint, marketplace-CI parity, diff review, test-behavior-change ask, single-logical-change signal, message
drafting, commitlint, confirm-and-commit) are assumed already complete, since the scenario states step 16
already succeeded — a commit cannot reach step 16 without them.

## Step 16 — Push (already done, per scenario)

`--push` was given, and this is not a nested `create-pr`-suppressed invocation, so step 16 always pushes
regardless of `commit_auto_push`. Push runs as `git push origin HEAD` (never a typed/interpolated branch
name). Per the scenario, this succeeded — the new commit is now the branch's head on `origin`.

## Step 16.5 — Bypass attestation for an already-open PR

This step fires because both of its preconditions are met: `--bypass-codex-review "urgent fix"` was
given, **and** step 16 actually pushed. (If step 16 had been skipped — nested `create-pr` invocation, or
the push declined — step 16.5 would be skipped entirely too; neither applies here.)

**(a) Empty-reason check.** Reason is `"urgent fix"` — non-empty. Continue (an empty/missing reason would
have caused this whole step to be treated as never passed, with no error).

**(b) Check whether a PR is already open.** Run `gh pr view --json number,url,headRefOid,labels`. Per the
scenario ("a branch with an already-open PR"), this returns a real PR: its `number`, `url`,
`headRefOid` (the just-pushed new head SHA), and current `labels`. Since a PR **does** exist, this step
attests directly here — it does *not* defer to step 17's Auto-PR flow (that deferred path is only for
"no PR exists yet").

**(c) Bot-trigger-mention check.** Scan the reason text `"urgent fix"` for a literal bot-trigger mention
(e.g. `@codex review`, `@codex full review`, `@coderabbitai review`). None found. Continue — the reason
is safe to post verbatim as a PR comment later (it never gets that far in this run, since (d) stops it,
but the check itself passes).

**(d) Resolve identity and verify merge-capable permission — this is where the scenario's failure
occurs.**

- Resolve `{owner}/{repo}` from (b)'s own `url` field (never a separate `gh repo view`).
- Resolve the current actor: `gh api user --jq '.login'`.
- Verify live permission: `gh api repos/{owner}/{repo}/collaborators/{actor}/permission --jq
  '.permission'` → returns **`read`**.
- `read` is **not** one of the accepted levels (`write`, `maintain`, `admin`).
- Per the skill's own instruction: *"If insufficient, stop here and report the bypass was not attested —
  the push already succeeded; only the attestation is skipped."*

**Execution stops inside step 16.5(d).** Sub-steps (e), (f), and (g) never run:
- **(e)** (build the `jq -n --arg`-constructed attestation JSON marker and post it as a PR comment) is
  **not** reached.
- **(f)** (verify/re-apply the `s: codex review bypassed` label, removing and re-adding it if already
  present) is **not** reached — the label is left completely untouched; nothing about it changes.
- **(g)**'s *success*-report branch is not reached either. Instead, this falls under (g)'s own
  failure-handling instruction, which spans "any failure in (c)-(f)": *"state clearly that the push
  succeeded but the bypass was **not** attested, and why — never report a failed attestation as if it
  succeeded."*

No PR comment is posted. No label is added, removed, or re-applied. The `Publish Codex policy result`
check on the pushed commit is left exactly as it already was — this step never touched it.

## Step 17 — Auto-PR

Not a nested `create-pr` invocation, so this step is evaluated normally. It checks `gh pr view --json
number` for the current branch: a PR is already open (the same one found in 16.5(b)). Per step 17's own
rule — *"If a PR is already open, skip this step entirely"* — this step is skipped, no new PR is created.

Because 16.5(b) found the PR immediately (rather than deferring the bypass request to this step), there
is no "deferred bypass had no effect" disclosure to make here — the bypass wasn't deferred, it was
attempted directly in 16.5 and failed there for a documented reason (insufficient permission), not
because step 17 dropped anything.

## Step 18 — Show the result

The final result report states:

1. **Commit**: hash, files changed, insertions/deletions (from the commit that already happened before
   this scenario's window).
2. **Push status**: pushed successfully to `origin/HEAD` via `git push origin HEAD`.
3. **Bypass attestation status — NOT attested.** Reported plainly, not silently:
   - The push succeeded; only the Codex-review-bypass attestation was skipped.
   - Reason: the current actor's live permission on this repo is `read`, which does not meet the
     required `write`/`maintain`/`admin` threshold checked at step 16.5(d).
   - No attestation comment was posted to the PR, and the `s: codex review bypassed` label was neither
     applied nor re-applied.
   - The `Publish Codex policy result` check for the new head commit (`headRefOid` from 16.5(b)) remains
     whatever it already was — unaffected by this run.
4. **Auto-PR**: skipped — a PR was already open for this branch (no duplicate PR created, nothing to
   report as dropped).

Net effect of this run: the code is pushed and live on the remote branch, but the Codex review bypass the
user asked for did **not** take effect. The user (or someone with sufficient repo permission — write,
maintain, or admin) would need to re-run the bypass attestation themselves, or obtain elevated permission,
for the bypass to actually apply to this commit's `Publish Codex policy result` check.
