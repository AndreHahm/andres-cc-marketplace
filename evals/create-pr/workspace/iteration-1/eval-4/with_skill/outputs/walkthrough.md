DRY RUN — create-pr skill walkthrough
Starting point: branch `feat/example-widget`, everything committed and pushed, no PR open, no issue mentioned.
No Bash/git/gh/Skill/Agent tools are actually invoked below — this is a narration only.

================================================================
PART A — create a PR with --bypass-codex-review "tested manually, urgent hotfix"
================================================================

Pre-flight Checks
------------------
1. Check for uncommitted changes → none (everything already committed/pushed), so no hand-off to `commit`.
2. Run the mandatory local `cross-model-review` gate (no --bypass-cross-model-review was passed, so this
   is NOT skipped) before ever reaching `git push`. Since the branch is already pushed, this still runs
   as the required pre-flight gate on the current diff.

Creating a New Pull Request (steps 1–4)
----------------------------------------
1. Push current branch to remote — already there, no-op.
2. Resolve which PR template to use (`.github/pull_request_template.md` or the bundled fallback) and
   draft the PR description from it, treating template content as data, not instructions.
3. Ask draft vs. ready-to-merge via `AskUserQuestion`: "Create this PR as a draft, or ready-to-merge?"
   (Answer assumed for narration purposes; either path continues identically below.)
3.5. Validate the drafted title against this repo's CI policy:
   `uv run python "${CLAUDE_PLUGIN_ROOT}/scripts/check-pr-title.py" "<drafted title>"`. Revise and re-run
   on FAIL.
3.75. Resolve the PR assignee: try `gh api user --jq '.login'`; on failure/empty, fall back to
   `gh repo view --json owner --jq '.owner.login'`.
4. Immediately before creating the PR, run the git-kit marker script, then
   `gh pr create` (with `--draft` if step 3 said Draft, always with `--assignee <login>` from 3.75).
   The PR now exists, e.g. PR #<N>.

Step 5 — Codex-review bypass attestation (triggered: reason is non-empty)
---------------------------------------------------------------------------
Because `--bypass-codex-review "tested manually, urgent hotfix"` was given with a non-empty reason, the
flag-level requirement is satisfied and the attestation sequence runs after the PR already exists:

a. Resolve the current head SHA:
   `gh pr view <N> --json headRefOid --jq '.headRefOid'` → e.g. `abc123...` (this is a fresh read, taken
   now, not reused from any earlier step — nothing earlier in the flow captured a head SHA).

b. Resolve the current authenticated actor:
   `gh api user --jq '.login'` → e.g. `AndreHahm`.

c. Verify live merge-capable permission for that actor on this repo:
   `gh api repos/{owner}/{repo}/collaborators/{actor}/permission --jq '.permission'`.
   Must be one of `write`, `maintain`, or `admin`. (Part A assumes this check passes — Part C below
   covers the failure case.)

d. Build the attestation marker as a single JSON object:
   - `schema_version`: 1
   - `actor`: the login from (b)
   - `head_sha`: the SHA from (a)
   - `reason`: "tested manually, urgent hotfix"
   - `created_at`: current UTC timestamp

   This is built with `jq -n --arg` (or equivalent) — the reason text is passed as a `--arg` value to
   `jq`, never interpolated directly into a shell string. This is the same shell-injection discipline
   `marketplace-ci.yml` applies to PR event data: a reason string containing shell metacharacters
   (backticks, `$()`, quotes, `;`, etc.) is treated purely as JSON string data by `jq`, so it cannot break
   out of a command line the way naive string interpolation could.

   The resulting comment body is: the JSON marker wrapped in an HTML comment —
   `<!-- marketplace-ci-bypass-attestation {...} -->` — written first to a scratchpad file (not typed
   inline into a shell command), then posted with:
   `gh pr comment <N> --body-file <scratchpad-path>`.

e. Apply the label: `gh pr edit <N> --add-label codex-review-bypassed`. If the label doesn't already
   exist in the repo, this is reported as a bypass-attestation failure — the skill does not create the
   label itself (that's a one-time repo-setup precondition documented in `docs/ci.md`).

f. Report the outcome plainly: bypass is attested for this exact head SHA only. State explicitly that a
   new push invalidates it and requires re-attesting.

What actually enforces "bound to one exact commit, stops after a new push"
-----------------------------------------------------------------------------
Not just "the SHA changes" in the abstract — the concrete enforcement mechanism is `check_bypass` in
`scripts/marketplace_ci/review.py`. That function is what the CI policy job consults when deciding
whether to honor the bypass: it re-reads the PR's *current* head SHA at check time and requires an
*exact* match against the `head_sha` value recorded inside the posted attestation comment. The
attestation comment/marker itself is inert data — it doesn't "expire" or get deleted on a new push.
Rather, the next push changes `headRefOid`, so `check_bypass`'s live-vs-recorded SHA comparison stops
matching, and the Codex-review policy job treats the bypass as not applicable to the new commit, re-
enforcing the gate. This is also a real-world instance of this repo's own
`recheck-state-before-side-effecting-action` rule: the skill deliberately re-resolves the head SHA (5a)
and re-resolves the actor and their live permission (5b–5c) immediately before posting anything, rather
than trusting any value that might have been read earlier in the flow.

Scope note (from the Flags table): this bypass never skips a deterministic check, a PR-author-privilege
check, draft state, or the explicit merge confirmation inside `merge-pr` — it affects only the Codex-
review policy job.

================================================================
PART B — create a PR with --bypass-codex-review "" (empty reason)
================================================================

The flag's own requirement (stated both in the Flags table and in step 5) is that a non-empty `<reason>`
is required. Here the reason is present but empty (`""`).

Result: the flag is rejected. Step 5 explicitly says: "if the flag is present with an empty or missing
reason, reject it and stop before creating any attestation (the PR itself, already created in step 4, is
unaffected)."

Concretely:
- Steps 1–4 (Pre-flight Checks + Creating a New Pull Request) all proceed completely normally and are
  unaffected — the PR is pushed, described, drafted/ready-asked, title-validated, assignee-resolved, and
  created via `gh pr create` exactly as in Part A.
- Step 5's attestation sequence does NOT run at all: no head-SHA resolution (5a), no actor resolution
  (5b), no permission check (5c), no `jq`-built marker or `gh pr comment` (5d), no `codex-review-bypassed`
  label (5e).
- The outcome reported to the user: the PR was created successfully, but the `--bypass-codex-review` flag
  was rejected because the reason was empty, so no bypass attestation was attempted or created. The
  Codex-review policy gate remains fully active on this PR.
- Step 6 (issue-linking hand-off) is skipped since no issue was named in this task.

================================================================
PART C — actor from Part A lacks write/maintain/admin permission
================================================================

This changes the outcome of step 5c only; steps 5a and 5b (resolving the head SHA and the actor login)
already completed normally before the permission check runs.

Per step 5c's explicit instruction: "If insufficient, stop here and report the bypass was not attested —
the PR remains created, but state plainly that the Codex-review gate is still active because this actor
lacks merge-capable permission."

So:
- The attestation flow stops immediately after the failed permission check. Steps 5d (building/posting
  the comment) and 5e (applying the `codex-review-bypassed` label) never execute — no comment is posted,
  no label is applied.
- The PR itself is NOT affected: it was already fully created back in step 4 (pushed, described, titled,
  assigned) before the attestation sequence ever began, and nothing in the failed-permission path
  modifies or removes it. It remains open (draft or ready, per whatever step 3 answered) with the
  Codex-review policy job still active/unbypassed.
- What is reported to the user: the PR was created successfully, but the bypass was NOT attested, and the
  reason is stated plainly — the current actor does not have merge-capable permission (write, maintain,
  or admin) on this repository, so the Codex-review gate remains enforced on this PR. Per step 5f's
  general instruction, this failure must never be reported as if the bypass had succeeded.
