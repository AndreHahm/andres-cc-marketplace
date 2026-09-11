# Skill-Invocation Transcript: `merge-to-completion` — PR #92 / ENG-518

## Pre-flight verification (real tool calls, before invoking the skill's own procedure)

Per the eval instructions, I confirmed the scenario's referenced PR/issue are not real live data before proceeding:

```
gh --version
→ gh version 2.88.1

gh auth status
→ Logged in to github.com account AndreHahm (keyring), active account: true

gh pr view 92
→ REAL result: PR #92 exists in this repo, but it is title
  "fix(ci): narrow await-codex-review triggers to Codex's real re-review conditions",
  state MERGED, unrelated to any Linear issue ENG-518 or to the acceptance-criteria
  scenario described in this task.
```

**Finding:** PR #92 in this actual repository is a real, already-merged, but *unrelated* PR. There is no real Linear issue ENG-518 reachable from this environment (no Linear MCP write/read is sanctioned here — see below). Every GitHub/Linear value used from this point forward that pertains to *this scenario's* PR #92/ENG-518 is **[SIMULATED]**, clearly marked, and not drawn from the real `gh pr view 92` output above.

I also checked the plugin's real configuration files, since `merge-to-completion` depends on them:

```
cat plugins/workmanagement-kit/host-profile.json
→ notion.read/write, linear.read/write all "support_status": "unconfigured", connector: null

git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json"
→ exit 1, "did not match any file(s)" → confirmed-untracked path is the only one that
  could honor an override

ls -la .claude/workmanagement-kit.local.json
→ No such file or directory → no override exists at all, on disk or tracked

cat plugins/workmanagement-kit/versioned-configuration.json
→ repository_policy.provider_profile: null, gate_discovery: "unconfigured"
```

**Real finding to disclose:** in this actual worktree, no installer has ever run Foundational Setup — `host-profile.json` ships with every Notion/Linear operation `unconfigured` (no connector sanctioned for real reads or writes), and `versioned-configuration.json`'s `repository_policy.provider_profile` is literally `null`, not `"git-kit"`. Read *literally*, `repository-gates`' own step 2 ("if `provider_profile` is unset/unconfigured... stop with a manual handoff") would halt here. However, `FOUNDATION_CONTRACTS.md`'s Repository Policy Profile section states the profile "is fixed — `git-kit` for every governed operation" for this specific repository as documented canonical policy, and the scenario states the PR "merged cleanly via the standard merge flow." I'm treating this as a **live drift finding** (the versioned-configuration.json file hasn't been updated to reflect the canonical fixed profile it's supposed to encode) rather than a blocker, and proceeding under the documented `git-kit`-for-everything profile — but this is a real gap worth flagging to the user, not silently smoothed over.

Everything below follows `merge-to-completion`'s own numbered procedure exactly.

---

## Merge phase

### Step 1 — Resolve policy (`repository-gates`)

Invoke `Skill(repository-gates)`. Per its own "Resolving the Repository Policy Profile" section: read `versioned-configuration.json` (done above — `provider_profile: null`), run the trust-boundary check on `.claude/workmanagement-kit.local.json` (done above — confirmed-untracked, and in fact absent entirely, so no override to honor). Given the canonical `FOUNDATION_CONTRACTS.md` table's fixed answer for this repo, the resolved provider for the "Merge" governed operation is `git-kit:merge-pr`.

**Disclosed:** the live `versioned-configuration.json` value (`null`) disagrees with the canonical table's stated fixed profile — reported to the user as drift, not silently reconciled.

### Step 2 — Verify readiness

Not duplicated here. Delegated entirely to `git-kit:merge-pr`'s own step 2 (five required checks: not-draft, status checks, no-changes-requested, no-merge-conflicts, not-behind-base) at step 5 below. Per the skill's own text, unresolved review threads are disclosed by `merge-pr` at its confirmation step, never treated as a blocking gate by this skill.

### Step 3 — Read Linear context

**[SIMULATED]** — read (not write) the Linear Issue for identity and acceptance criteria, without treating Linear's state as GitHub merge authority:

```
[SIMULATED] mcp__claude_ai_Linear__get_issue(id: "ENG-518")
→ id: ENG-518
  title: "<simulated placeholder title for ENG-518>"
  status: "In Review"
  acceptance_criteria (4):
    AC1: "<simulated placeholder — criterion 1 text>"
    AC2: "<simulated placeholder — criterion 2 text>"
    AC3: "<simulated placeholder — criterion 3 text>"
    AC4: "<simulated placeholder — criterion 4 text>"
  linked PR: #92 (github-link field)
```

Note: because `host-profile.json`'s `linear.read` is genuinely `unconfigured` in this environment, this read would fail closed against a real connector (per the Host Profile contract — "tool presence in a session is never proof of permission"). This transcript marks it `[SIMULATED]` for exactly that reason, doubly so: no real ENG-518 exists, and no real Linear connector is sanctioned here either.

### Step 4 — Present and confirm (merge method, branch behavior, disposition workflow)

`AskUserQuestion`:

> "PR #92 (ENG-518) is ready to be checked for merge. Proposed: delegate to `git-kit:merge-pr` (squash merge, per repo default `pr_merge_type`), then record `pr-merged` from GitHub's own read-back, then run a separate Linear disposition pass comparing all 4 acceptance criteria individually — even though you've noted the implementer already verified them, this skill does not skip the comparison, it just expects it to go quickly. Proceed?"
> Options: **Yes — proceed** / **No — stop here**

Assume **Yes** (per the task framing — "merged cleanly," "record delivery after merge").

### Step 5 — Delegate

Invoke `Skill(git-kit:merge-pr)` with `$ARGUMENTS = 92`.

**[SIMULATED]** trace of what `merge-pr` would do against the real repo, since PR #92 is real but not this scenario's PR — describing its steps rather than executing them:
- Step 1: `gh pr view 92 --json number,isDraft,headRefName,...` — resolve `{owner}/{repo}`, validate ref names.
- Step 1.5: session open-issues scan (N/A here — fresh session).
- Step 2: five required-checks pass (not-draft, status checks all passing, no CHANGES_REQUESTED, `mergeable: MERGEABLE`, `behind_by: 0`); advisory disclosures — `mergeStateStatus: CLEAN`, 0 unresolved review threads.
- Step 3: merge-rights check — `MERGE ALLOWED` (repo owner).
- Step 5 (its own confirm): `AskUserQuestion` — "Merge PR #92 via squash? mergeStateStatus CLEAN, 0 unresolved threads." → **Yes**.
- Step 6: reads `pr_merge_type` = `SQUASH` (matches scenario's "squash merge").
- Step 7: writes the `gh-pr-merge` marker, runs `gh pr merge 92 --squash --match-head-commit <verified-sha> --delete-branch`, then re-reads `gh pr view 92 --json state,mergeCommit` to confirm.
- Step 8: `AskUserQuestion` — "Run `finishing-work` now to sync local `main`?" → **[SIMULATED] Yes**, `merge-pr` invokes `Skill(git-kit:finishing-work)` itself, bound to PR #92.

### Step 6 — Read back the actual GitHub merge state and merge SHA

Never assumed from the request. This is exactly what `merge-pr`'s own step 7(e) already did (`gh pr view $ARGUMENTS --json state,mergeCommit`), and `merge-to-completion` reads that same read-back rather than trusting "the user said it merged cleanly":

```
[SIMULATED] gh pr view 92 --json state,mergeCommit
→ state: "MERGED"
  mergeCommit: { "oid": "a1b2c3d4e5f6789012345678901234567890abcd" }
```

`pr-merged` is recorded **only** because this read-back says `MERGED` — not because the task description asserted "merged cleanly."

### Step 7 — Record `pr-merged` via `linear-github-linking`

Invoke `Skill(linear-github-linking)` to append a `git-github-evidence` entry to the ENG-518 Issue, per `FOUNDATION_CONTRACTS.md`'s schema:

```json
[SIMULATED entry appended to ENG-518's git-github-evidence array]
{
  "evidence_id": "gge-92-merged-01",
  "repository": "AndreHahm/andres-cc-marketplace",
  "stage": "pr-merged",
  "branch": "<simulated head branch>",
  "base_branch": "main",
  "commits": [ /* pre-merge PR-branch commits, unchanged from prior stage entries */ ],
  "pull_request": {"number": 92, "url": "https://github.com/AndreHahm/andres-cc-marketplace/pull/92", "state": "merged"},
  "merge_commit_sha": "a1b2c3d4e5f6789012345678901234567890abcd",
  "gates": [ {"name": "Publish Codex policy result", "owner": "marketplace-ci", "result": "pass", "sha": "<head-sha>", "recorded_at": "2026-09-11T00:00:00Z"} ],
  "provider": "git-kit:merge-pr",
  "policy_profile": "git-kit-fixed (per FOUNDATION_CONTRACTS.md; versioned-configuration.json's own field currently null — drift disclosed above)",
  "supersedes": null,
  "transition_id": "tr-eng518-0N",
  "recorded_at": "2026-09-11T00:00:00Z"
}
```

`merge_commit_sha` carries the **read-back** SHA from step 6 — never placed in `commits[]`, per the schema's own note that a squash merge's SHA was never on the PR branch's own history.

### Step 8 — Confirm native communication

**[SIMULATED]** check of GitHub's own Linear integration (if configured for this workspace):

```
[SIMULATED] mcp__claude_ai_Linear__get_issue(id: "ENG-518")  (re-read, post-merge)
→ status: "In Review"   (unchanged — no native integration configured in this simulated workspace)
```

For this walkthrough, assume the native GitHub↔Linear integration **is** configured and, on merge, moved the Issue's workflow status to "Done" automatically (a common real-world behavior of that integration). Per step 8's explicit instruction:

> **This is reported as drift, not treated as the disposition.** The Issue's status field now reads "Done," but no explicit per-criterion Linear disposition has been run yet by this skill. That status change is GitHub's own integration acting informationally/automatically — it is not `merge-to-completion`'s own `work-closed` transition, and it did not go through the acceptance-criteria comparison steps 9-13 require. This is flagged to the user as a fact to reconcile (a candidate for `linear-github-reconciliation` if it turns out to be inconsistent with the disposition below), not accepted as "the issue is already closed, skip ahead."

---

## Linear disposition (separate, explicit step)

### Step 9 — Compare delivered change against each criterion individually

Even though the task states all 4 criteria "were already verified complete by the implementer during development, with nothing ambiguous," this skill does **not** substitute that assertion for its own comparison — it still performs an individual, criterion-by-criterion check against the actual delivered diff, never "merged, therefore done."

```
[SIMULATED comparison against PR #92's own diff/description]
AC1: "<simulated criterion 1>" — Met. Evidence: <simulated file/line or PR description excerpt>.
AC2: "<simulated criterion 2>" — Met. Evidence: <simulated file/line or PR description excerpt>.
AC3: "<simulated criterion 3>" — Met. Evidence: <simulated file/line or PR description excerpt>.
AC4: "<simulated criterion 4>" — Met. Evidence: <simulated file/line or PR description excerpt>.
```

Since the case is described as straightforward/unambiguous with nothing in question, this is **not** "large or ambiguous" — the optional `AskUserQuestion` gate for an independent `work-transition-reviewer` Acceptance check (dispatched via `bridge_caller.py` per `FOUNDATION_CONTRACTS.md`'s Codex Bridge-Caller Dispatch procedure) is available but not warranted here. Stating it explicitly rather than silently skipping it: **declined as unnecessary given the case's own straightforwardness**, not glossed over.

### Step 10 — Classify each item

All 4 criteria classify as **completed** (delivered change satisfies each, individually verified in step 9). No item falls into follow-up/retained-question/canceled/unresolved.

### Step 11 — Present and confirm disposition

`AskUserQuestion`:

> "Linear disposition for ENG-518: all 4 acceptance criteria individually compared and confirmed met by PR #92's merged change. No follow-ups, no cancellations. Note: GitHub's native Linear integration already moved the Issue's status to 'Done' on merge (reported above as drift, not as this disposition). Proposed: close ENG-518 as `work-closed`, since condition (a) — every criterion literally met, no outstanding item — is satisfied. Proceed?"
> Options: **Yes — close ENG-518** / **No — hold open, I'll review**

Assume **Yes**.

Since no outstanding criterion exists here, the "closing-now-with-the-gap-tracked" distinct-option branch (for condition (b)) does not apply — this is a pure condition-(a) case.

### Step 12 — Create/link approved follow-ups via `open-item-management`

**N/A for this scenario** — step 10 produced zero follow-up/retained/canceled items, so `Skill(open-item-management)` is not invoked. (Stated explicitly rather than silently omitted, per the skill's own procedure and the repo's disclose-before-overriding-decisions convention.)

### Step 13 — Close the Linear Issue

Condition (a) is satisfied: every criterion literally met, no outstanding item, confirmed at step 11. Record Wave 1's `work-closed` transition via `linear-work-management`, through the base Transition Contract (not a new schema field):

```json
[SIMULATED write via Skill(linear-work-management)]
mcp__claude_ai_Linear__save_issue(id: "ENG-518", stateId: "<Done state id>")

Transition Contract entry embedded on ENG-518:
{
  "transition_id": "tr-eng518-0N+1",
  "operation_id": "<connector op id, if provided>",
  "affected_record": {"system": "linear", "stable_id": "ENG-518"},
  "source_plugin": "workmanagement-kit",
  "verification_evidence": "read back via linear.read, confirmed prior status change (the native-integration drift from step 8) — per the next-write convention, this write's own verification_evidence describes the PRIOR write's read-back, not this one",
  "recorded_at": "2026-09-11T00:05:00Z"
}
```

**Note on the drift from step 8:** if GitHub's native integration had already flipped the Issue to "Done" before this explicit write, this write is effectively idempotent/reconciling — but it is still recorded as `merge-to-completion`'s own deliberate `work-closed` transition, not silently accepted as "already done by the integration." The distinction matters because the integration's automatic change carries no acceptance-criteria evidence; this transition does.

### Step 14 — Reopen if invalidated

N/A — no later evidence contradicts this closure in this scenario. (Documented as the fallback path, not exercised here.)

### Step 15 — Cleanup is already handled — never re-invoke it here

`git-kit:merge-pr`'s own step 8 (inside this skill's step 5 delegation) already asked "run `finishing-work` now?" and, on the simulated "Yes" above, invoked `Skill(git-kit:finishing-work)` itself, bound to PR #92. `merge-to-completion` holds **no tool grant** for `git-kit:finishing-work` (confirmed against its `allowed-tools` frontmatter: `Read, Write, Skill(linear-work-management), Skill(repository-gates), Skill(linear-github-linking), Skill(git-kit:merge-pr), Skill(open-item-management), Bash(bridge_caller.py:*), AskUserQuestion` — no `Skill(git-kit:finishing-work)` entry) and does not attempt to invoke it a second time. If cleanup were still needed for some reason step 5 didn't cover, that would be a fresh, separate request to `git-kit:finishing-work` outside this skill's flow — not exercised in this scenario since step 5's delegation already handled it.

---

## Summary of what was recorded

| Write | Mechanism | Value |
|---|---|---|
| `git-github-evidence` (`stage: pr-merged`) | `linear-github-linking` | `merge_commit_sha: a1b2c3d4e5f6789012345678901234567890abcd` [SIMULATED, keyed off real `gh pr view 92`'s read-back shape] |
| `work-closed` transition | `linear-work-management` | ENG-518 → Done, condition (a) [SIMULATED] |

**Drift disclosed, not silently resolved:**
1. `versioned-configuration.json`'s `repository_policy.provider_profile` is literally `null` in this repo, disagreeing with `FOUNDATION_CONTRACTS.md`'s canonical "fixed to git-kit" statement.
2. `host-profile.json` ships fully `unconfigured` for Notion/Linear, with no local override file present — every Linear read/write above is doubly simulated (no real ENG-518, and no real connector sanctioned).
3. GitHub's native Linear integration (assumed configured for this walkthrough) moved ENG-518's status on merge — reported as drift at step 8, never treated as the disposition itself; the actual `work-closed` transition only happened at step 13, after the explicit per-criterion comparison.

**Confirmed real, unrelated fact:** PR #92 in this repository is real, merged, and about `await-codex-review` trigger scoping — not about ENG-518 or this scenario's 4 acceptance criteria.
