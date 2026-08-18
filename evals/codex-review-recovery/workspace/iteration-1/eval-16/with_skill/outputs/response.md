# Simulated run: codex-review-recovery — PR #77

**Given setup (scenario-provided):** owner/repo `acme-org/acme-app`, PR #77, branch `feature/codex-recovery-demo`. Step 1's `headRefOid` = `abc123`. Step 6 re-verified `abc123` and posted `@codex review` successfully. Step 7 re-fetches the head one more time before rerunning `databaseId 300` (baseline attempt `1`, conclusion still `failure`) and now gets `def999` — a new commit landed on the PR during step 6's own comment-posting call.

---

## Step 1 — Resolve the PR

Command:
```
gh pr view 77 --json number,url,headRefName,headRefOid
```
Result:
```json
{
  "number": 77,
  "url": "https://github.com/acme-org/acme-app/pull/77",
  "headRefName": "feature/codex-recovery-demo",
  "headRefOid": "abc123"
}
```
`$ARGUMENTS` was `77` — no shell metacharacters, passes through untouched. Extracted `<owner>/<repo>` = `acme-org/acme-app` from the `url` field; this is passed as `-R "acme-org/acme-app"` to every subsequent `gh pr`/`gh run` call. Baseline head recorded: `abc123`.

## Step 2 — Check the current check state

Command:
```
gh pr checks 77 -R "acme-org/acme-app" --json name,workflow,bucket,link
```
Result (relevant entry):
```json
{"name": "Await Codex review", "workflow": "Codex review status", "bucket": "fail", "link": "https://github.com/acme-org/acme-app/actions/runs/900111"}
```
`workflow` matches the known display name (`Codex review status`) and `name` matches (`Await Codex review`) — exactly one matching entry. `bucket` is `fail` → this is the only state this skill acts on. Continue to step 3.

## Step 3 — Confirm with the human

`AskUserQuestion`:
> "The 'Await Codex review' check failed for PR #77. Have you confirmed on Codex's own dashboard that this PR's review actually finished?"
> Options: "Yes — retry" / "No — let me check first"

Given (implied by the scenario reaching step 6/7): the human answered **"Yes — retry."** Continue to step 4.

## Step 4 — Re-verify the head hasn't moved

Command:
```
gh pr view 77 -R "acme-org/acme-app" --json headRefOid --jq '.headRefOid'
```
Result: `abc123`

Matches step 1's `headRefOid` (`abc123`). No move detected. Continue to step 5.

## Step 5 — Resolve the workflow run to act on

Command:
```
gh run list --workflow await-codex-review.yml --repo "acme-org/acme-app" --branch "feature/codex-recovery-demo" \
  --limit 5 --json databaseId,headSha,conclusion,attempt
```
Result:
```json
[
  {"databaseId": 300, "headSha": "abc123", "conclusion": "failure", "attempt": 1},
  {"databaseId": 288, "headSha": "9f0e11c", "conclusion": "success", "attempt": 1}
]
```
`<headRefName>` (`feature/codex-recovery-demo`) contains no shell metacharacters — safe to interpolate.

Exactly one entry's `headSha` matches step 4's confirmed `abc123`: `databaseId 300`. Its `conclusion` is `failure` — not `success` (nothing to stop for), and it is one of the two legitimate "needs recovery" values (`failure`/`timed_out`). Proceed to step 6.

Baseline recorded for step 8's later polling: `databaseId = 300`, `attempt = 1`.

## Step 6 — Post the retry comment

Re-fetch immediately before posting, per the skill's step-6 requirement to re-check the head across step 5's own network round-trip:
```
gh pr view 77 -R "acme-org/acme-app" --json headRefOid --jq '.headRefOid'
```
Result: `abc123` (given) — still matches step 4's confirmed value. Continue.

Write the marker immediately before the guarded command:
```
"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-review codex-review-recovery
```
Result: marker written (exit 0).

Post the comment:
```
gh pr comment 77 -R "acme-org/acme-app" --body "@codex review"
```
Result (given): **success** — exit status 0, comment posted.

Per the scenario, a new commit landed on the PR during this very call (i.e., sometime between the head re-check that preceded it and the moment `gh pr comment` actually completed on GitHub's side) — invisible to this step, since step 6 only checks the head *before* posting, not after.

## Step 7 — Re-run the failed check

Per the skill, two things must be re-checked immediately before rerunning `databaseId 300`, because step 6's own network round-trip (posting the comment) may have changed either one — starting with the head:

Command:
```
gh pr view 77 -R "acme-org/acme-app" --json headRefOid --jq '.headRefOid'
```
Result (given): `def999`

**Decision point:** `def999` does not match step 6's confirmed value (`abc123`). Per the skill's explicit instruction — *"If it no longer matches step 6's confirmed value, apply step 4's own stop condition here too"* — this is a stop, not a proceed. The skill is explicit that this applies **regardless of whether the second re-check (the run's `conclusion`) would otherwise have passed** — the check is listed first specifically so a moved head is caught before the conclusion check or the rerun ever executes. I do **not** call `gh run view 300 --json conclusion`, and I do **not** call `gh run rerun 300` — nothing further happens in this step.

Rationale (per the skill's own stated reasoning for this stop, echoed from step 4): the workflow's `synchronize` trigger has already started a fresh `Await Codex review` run for the new head (`def999`) independently of this skill. Rerunning the stale `databaseId 300` (tied to the old head `abc123`) now risks colliding with that fresh run through the workflow's `concurrency: cancel-in-progress` group. The original `failure` this flow was recovering may no longer even apply to the PR's current state.

Flow **stops here**. Step 8 (polling) is never reached.

---

## Final response to the user

The PR's head moved again — I have to stop before rerunning.

**What happened:**
1. PR #77's `Await Codex review` check had failed at head `abc123`; you confirmed Codex's dashboard showed the review done.
2. I re-verified the head was still `abc123`, then posted `@codex review` — that comment **was posted successfully**.
3. Immediately before rerunning the failed check (run `databaseId 300`, attempt 1, still `failure`), I re-fetched the head one more time as required, and it now reads `def999` — a new commit landed on the PR during the comment-posting step itself.

**Why I stopped instead of rerunning:** a moved head means GitHub's own `Await Codex review` workflow has already kicked off a *fresh* run for `def999` via its `synchronize` trigger, independent of anything this skill does. Rerunning the old run (`databaseId 300`, still pinned to `abc123`) now risks colliding with that fresh run through the workflow's `concurrency: cancel-in-progress` group — and the original `failure` I was recovering may no longer even be relevant to the PR's current state.

**Where things stand:**
- The `@codex review` comment I posted at the old head is already on the PR — it's harmless, but it was aimed at the `abc123` state.
- Run `databaseId 300` was **not** rerun.
- A new `Await Codex review` run should already be in flight for the new commit (`def999`) — check that one directly (PR checks tab) rather than the old run I was tracking.
- If that new run also ends up stuck in the same "Codex finished on the dashboard but GitHub shows nothing" state, come back and re-run this recovery flow from the top for the new head — it'll need its own fresh dashboard confirmation (step 3 isn't something I can carry over from this attempt).
