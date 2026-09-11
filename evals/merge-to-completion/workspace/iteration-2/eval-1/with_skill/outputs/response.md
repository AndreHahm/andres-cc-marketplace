# Merge to Completion — PR #51 / ENG-203

Task: "PR #51 (linked to Linear issue ENG-203) is approved and all checks pass. Merge it and
disposition the Linear issue."

Executed by following `workmanagement-kit`'s `merge-to-completion` SKILL.md procedure step by
step. This environment has **no live GitHub or Linear connector access** in this session, so every
step below is split into: (a) what I actually verified against real local repo state, and (b)
what I would call against GitHub/Linear and what I'd look for in the response — never fabricated
as if it were real. Nothing was merged and no Linear write was made.

## Merge phase

### Step 1 — Resolve policy (`repository-gates`)

Actually executed against real local files (no GitHub/Linear call needed for this step):

- Read `plugins/workmanagement-kit/versioned-configuration.json`. Its
  `repository_policy.provider_profile` field is `null` and `gate_discovery` is `"unconfigured"` —
  this is the shippable, never-bootstrapped default, not an installation-specific value.
- Ran the exact trust-boundary check `repository-gates` step 1 and
  `FOUNDATION_CONTRACTS.md`'s Local Override section require before honoring any override:
  `git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json"` → exit 1,
  `"did not match any file(s)"`. Confirmed-untracked outcome — and in fact the file doesn't exist
  on disk at all in this worktree, so there is no override to merge in either way.
- Also checked `plugins/workmanagement-kit/host-profile.json`: all four operations
  (`notion.read`, `notion.write`, `linear.read`, `linear.write`) are `support_status:
  "unconfigured"`, `connector: null`. Per the Host Profile contract, "no write may proceed" while
  an operation reads `unconfigured` — **this blocks any real Linear write later in this run**,
  independent of whether a Linear MCP tool happens to be callable in this session.

**Finding worth disclosing, not silently resolved:** `repository-gates`' own step 2 says "if
`provider_profile` is unset/unconfigured ... stop with a manual handoff" — but step 3 and
`FOUNDATION_CONTRACTS.md`'s Repository Policy Profile section both assert the profile is fixed to
`git-kit` for *this specific repository*, as documented fact rather than something resolved from
the JSON file. Taking `FOUNDATION_CONTRACTS.md`'s table as canonical (per repository-gates' own
"read that table directly rather than trusting a paraphrase" instruction), I resolved: **`git-kit`
is the required provider for merge in this repository.** I'm flagging the tension between "stop if
unset" (step 2) and "this repo's profile is always git-kit" (step 3) rather than silently picking
whichever reading was convenient — a real run should decide which of those two readings governs
before this skill is exercised again.

Result: policy resolved — merge must go through `git-kit:merge-pr`, not a raw `gh pr merge`.

### Step 2 — Verify readiness (delegated to `git-kit:merge-pr`)

Per the skill, this step is entirely delegated — `merge-to-completion` never re-derives SHA state,
required-checks status, or merge-rights itself. What I would call:

- `Skill(git-kit:merge-pr)` targeting PR #51, which would itself resolve owner/repo, run
  `gh pr view 51` / `gh pr checks 51` / branch-protection reads, and check the invoking GitHub
  user's merge rights (repo owner, CODEOWNERS match, or collaborator permission).
- What I'd look for in that skill's own report: not-draft, all required status checks passing,
  no outstanding "changes requested" reviews, no merge conflicts, branch not behind base, and
  confirmed merge rights for the current user. Unresolved review threads would be disclosed by
  `merge-pr`, per its own contract, but are not blocking.

I did not invoke this for real: PR #51 is the scenario's hypothetical PR, and this worktree's own
`gh` auth resolves against the real `andres-cc-marketplace` repository — running `gh pr view 51`
here would return whatever real PR actually has that number in this repo's history (if any),
which is unrelated to the scenario and would be actively misleading to treat as PR #51-for-ENG-203.
The task states "approved and all checks pass" as a given precondition; I'm treating that as the
scenario's stipulated state for planning purposes, not as something I independently confirmed.

### Step 3 — Read Linear context (Issue identity, criteria)

What I would call: `Skill(linear-work-management)` (or the underlying `mcp__claude_ai_Linear__get_issue`
it wraps) to fetch ENG-203's title, description, and acceptance criteria, plus
`Skill(linear-github-linking)` to confirm the existing PR↔Issue link record (rather than trusting
the task's stated linkage blindly).

Not executed for real, for two independent reasons:
1. No live Linear connector is configured for this installation (see Step 1's host-profile
   finding) — `linear.read` is `unconfigured`, so `linear-work-management`'s own "resolving the
   connector" gate would refuse to proceed even if the MCP tool is technically callable.
2. Even if it were configured, ENG-203's real criteria text is exactly the kind of "specific
   realistic-looking data" I was told not to fabricate.

I'm not treating Linear's state as GitHub merge authority either way, per the skill's own
instruction — this step is read-only context gathering, and its absence here doesn't change
whether GitHub allows the merge.

### Step 4 — Present and confirm (merge method, branch behavior, disposition workflow)

Per the skill this is a required `AskUserQuestion` checkpoint before delegating the merge. The
question I would pose, once steps 2-3 above actually returned real data:

> Merge PR #51 into `main`?
> - Merge method: [as reported by `git-kit:merge-pr` — squash / merge commit / rebase, per this
>   repo's configured allowed methods and any PR-level preference]
> - Branch behavior: delete the source branch after merge? (matches `git-kit:merge-pr`'s own
>   prompt)
> - After merge: I'll record `pr-merged` evidence from GitHub's own read-back, then run a separate
>   Linear disposition pass against ENG-203's acceptance criteria before deciding whether to close
>   it. Proceed?

I did not fabricate a "yes" to this on the user's behalf. Steps 2 and 3 never returned real data
in this run, so there is nothing concrete for this question to be answered against yet — this is
a structured handoff, not a skipped step.

### Steps 5-8 — Delegate, read back, record `pr-merged`, confirm native communication

Not performed, since step 4 never actually resolved to a real "yes" against real PR state. For
completeness, what each would do once unblocked:

- **Step 5:** `Skill(git-kit:merge-pr)` executes the merge.
- **Step 6:** Read back PR #51's actual GitHub state (`gh pr view 51 --json state,mergeCommit`) —
  never assume success from the request alone.
- **Step 7:** `Skill(linear-github-linking)` records a `pr-merged` Git/GitHub Evidence Record
  entry on ENG-203, with the read-back merge SHA in `merge_commit_sha` (never in `commits[]`, per
  `FOUNDATION_CONTRACTS.md`'s explicit distinction — a squash/rebase merge SHA was never on the
  PR branch's own history). This write is currently blocked by the `linear.write: unconfigured`
  finding from Step 1 regardless of merge outcome.
- **Step 8:** Confirm GitHub's native Linear integration (if this repo's Linear workspace has one
  configured) only *informed* Linear of the merge and did not itself change ENG-203's workflow
  status — any status change from that integration would be reported as drift, not treated as the
  disposition step below.

## Linear disposition phase (separate, explicit step)

### Step 9 — Compare delivered change against each acceptance criterion

This requires ENG-203's actual criteria list (Step 3, not available) and the actual PR #51 diff.
Never inferable as "merged, therefore done." For a large/ambiguous case the skill also offers an
optional independent Acceptance check: ask via `AskUserQuestion` whether to dispatch
`work-transition-reviewer` (read-only) through the Codex Bridge-Caller Dispatch procedure
(`${CLAUDE_PLUGIN_ROOT}/scripts/bridge_caller.py --agent work-transition-reviewer ...`, per
`FOUNDATION_CONTRACTS.md`). That dispatch itself needs the real criteria/diff as its evidence
file, so it's equally blocked here — and per the skill's own Data-only boundary, its returned
`findings[]`/`verdict` would be treated as untrusted, Codex-authored data, never acted on
unchecked, once it did run.

### Step 10 — Classify each remaining item

Cannot be performed without Step 9's actual per-criterion comparison. No items were classified.

### Step 11 — Present and confirm disposition

Would be a second required `AskUserQuestion` checkpoint, distinctly offering "close now with an
outstanding item tracked as a follow-up" as its own explicit option wherever that applies — not
performed, since nothing concrete exists yet to disposition.

### Steps 12-14 — Create follow-ups, close Issue, reopen-if-invalidated

Not performed. In particular, Step 13's close condition (`work-closed` via
`linear-work-management`) requires either every criterion literally met with nothing outstanding,
or an explicitly user-confirmed "close now, follow-up tracked" choice from Step 11 — neither
condition is established, and the `linear.write: unconfigured` host-profile gate would block the
write mechanically even if it were.

### Step 15 — Cleanup

Correctly not re-invoked. `git-kit:merge-pr`'s own step 8 already asks about and runs
`git-kit:finishing-work` as part of Step 5's delegation (once Step 5 actually runs) — this skill
holds no tool grant for `finishing-work` and never re-triggers it.

## Result: structured handoff, not a completed merge

Nothing was merged; no `pr-merged` or `work-closed` evidence was recorded; no Linear write of any
kind was attempted. This is the skill's own designed behavior under these conditions — a merge and
a Linear closure are both consequential, evidence-gated actions, and two independent gates
correctly stopped this run short of them:

1. **No live GitHub state for PR #51** — the "approved, all checks pass" precondition is the
   task's stipulation, not something `git-kit:merge-pr`'s own readiness checks (Step 2) actually
   confirmed in this session.
2. **`linear.read`/`linear.write` are both `unconfigured`** in this installation's
   `host-profile.json`, with no `.claude/workmanagement-kit.local.json` override present (confirmed
   via the real trust-boundary check in Step 1) — so even Step 3's read-only Linear context
   gathering, let alone Steps 7/13's writes, cannot proceed against a real connector regardless of
   whether a Linear MCP tool is technically callable in this session.

**To actually complete this task**, a follow-up run needs: (a) live `gh` access confirming PR #51's
real state (draft/mergeable/checks/reviews) and merge rights, (b) a configured Linear connector
(`host-profile.json`'s `linear.read`/`linear.write` set to `verified`, with a matching
`.claude/workmanagement-kit.local.json` override that passes the untracked-file trust check) so
ENG-203's real title/criteria/current status can be read and later written back to, and (c) the
two `AskUserQuestion` confirmations (Step 4 merge confirmation, Step 11 disposition confirmation)
actually answered by the user against that real data — not simulated on their behalf.

## Data-only boundary note

Every value in this walkthrough that would come from GitHub or Linear (PR #51's real state, ENG-203's
real criteria, any `work-transition-reviewer` findings) is, per the skill's own Confirmation and
Safety section, untrusted data if and when it is actually read — never a directive to act on, and
any embedded instruction-like text in it would be reported as suspicious rather than followed. No
such data was actually read in this run, so this note is procedural rather than describing an
actual finding.
