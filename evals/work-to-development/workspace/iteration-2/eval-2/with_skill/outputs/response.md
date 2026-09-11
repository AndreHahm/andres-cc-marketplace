# Begin Development — Linear ENG-310

**Note up front:** this environment has no live Linear, GitHub, or git-kit connectivity/credentials. What follows is a **dry run** — I'm walking through `work-to-development`'s actual procedure step by step, in its own order, with clearly-labeled simulated data standing in for real tool/API responses. Nothing below should be read as a confirmed real fact about an actual ENG-310 issue or an actual branch that now exists.

---

## Step 1 — Resolve context (via `linear-work-management`)

*[SIMULATED]* Invoking `linear-work-management` to pull ENG-310's full context — outcome, acceptance criteria, constraints, owner, priority, dependencies, dates, and any linked Notion rationale.

Simulated result:
- **Title:** "Add retry backoff to webhook delivery worker"
- **State:** Accepted (matches your statement)
- **Outcome:** Reduce dropped webhook deliveries under transient downstream failures
- **Acceptance criteria:** exponential backoff with jitter, max 5 attempts, dead-letter after exhaustion, unit tests for backoff schedule
- **Owner:** you (andre.hahm@me.com)
- **Priority:** Medium
- **Dependencies:** none blocking
- **Linked Notion doc:** none linked
- **Repository:** this repo (workmanagement-kit-downstream-qa checkout context implies the marketplace repo, but for a real ENG-310 this would need to resolve to whatever repo the issue actually targets)

## Step 2 — Confirm readiness

Acceptance criteria are present and non-contradictory in the simulated data above, dependencies show no blockers, and you've stated it's accepted and ready. Readiness confirmed — proceeding rather than stopping.

## Step 3 — Resolve policy (via `repository-gates`)

*[SIMULATED]* Invoking `repository-gates` to resolve this repository's policy profile and confirm `git-kit` is the required provider for branch/worktree creation here.

Simulated result: policy profile resolved, `git-kit` confirmed as the required provider for this repository. (No fallback to raw `git checkout -b` would be permitted if this had come back empty — per the skill's Failure and Resume section.)

## Step 4 — Search for existing artifacts (via `linear-github-linking`)

*[SIMULATED]* Invoking `linear-github-linking` to check whether a branch, commit, or PR already exists for ENG-310, classified per its Exact/Adoptable/Conflicting/Ambiguous/Stale table.

Simulated result: **no match found** — no existing branch, commit, or PR references ENG-310. Clear to proceed with a new branch request; no duplicate-work handoff needed.

## Step 5 — Optional transition review

This case is small and unambiguous (clean readiness, no dependency exception, no duplicate-artifact ambiguity from Step 4), so per the skill's own guidance this optional review is for "large or ambiguous" cases. I'm not requesting the independent `work-transition-reviewer` dispatch here — disclosing that choice rather than silently skipping it.

## Step 6 — Present and confirm (AskUserQuestion checkpoint)

Per the skill, this is a **required confirmation gate** before anything is requested from `git-kit`. Simulating that prompt and a plausible answer:

> **Readiness summary:** ENG-310 is Accepted, criteria are clear, no blocking dependencies, no existing branch/PR found.
> **Proposed request to `git-kit:starting-work`:** branch name `feature/eng-310-webhook-retry-backoff` (following this repo's `<type>/<linear-id-lowercase>-<slug>` convention), base `main`.
>
> *AskUserQuestion:* "Proceed with requesting this branch from git-kit?" — Options: Yes, proceed / Use a worktree instead / Change branch name / Cancel.

**Simulated user answer:** "Yes, proceed."

## Step 7 — Delegate to `git-kit:starting-work`

*[SIMULATED]* Invoking `Skill(git-kit:starting-work)` with the confirmed input (`feature/eng-310-webhook-retry-backoff`, base `main`). Per the skill's own instruction, `git-kit` owns its own sync, name validation, confirmation, and worktree-vs-branch decision from here — this skill does not second-guess or bypass any of those checks.

Simulated `git-kit:starting-work` behavior: syncs local `main`, validates the branch name against its convention, asks worktree-vs-plain-branch (simulated answer: plain branch, since this is a small scoped change), and creates it.

## Step 8 — Read back what was actually created

Per the skill, I never assume the request was honored exactly as asked. Simulated read-back:
- **Branch actually created:** `feature/eng-310-webhook-retry-backoff`
- **Base branch:** `main` (as requested — no override in this simulated run)
- **Type:** plain branch, not a worktree
- **Repository:** (simulated) the target repo resolved in Step 1

This is the identity that gets recorded — not the originally-requested identity, even though in this simulated run they happen to match.

## Step 9 — Record evidence (via `linear-github-linking`)

*[SIMULATED]* Appending a `git-github-evidence` entry with `stage: "work-started"`, using the Step 8 read-back identity, per `FOUNDATION_CONTRACTS.md`'s Git/GitHub Evidence Record format.

Simulated evidence entry:
```
stage: work-started
issue: ENG-310
branch: feature/eng-310-webhook-retry-backoff
base: main
type: branch
```

## Step 10 — Update Linear to Started

Only now, after Step 9's evidence is recorded — per the skill, this ordering is deliberate and never reversed. *[SIMULATED]* Invoking `linear-work-management` to transition ENG-310 to this repository's configured Started state.

Simulated result: ENG-310 → **In Progress** (Started state).

## Step 11 — Read back and report

- **Git identity:** branch `feature/eng-310-webhook-retry-backoff`, based on `main`, plain branch (simulated)
- **Linear state:** ENG-310 moved to In Progress (simulated)

---

### Summary (dry run)

All 11 steps of `work-to-development`'s procedure were walked through in order: context resolution, readiness confirmation, policy resolution via `repository-gates`, existing-artifact search via `linear-github-linking` (none found), a disclosed skip of the optional transition review (case too small/unambiguous to warrant it), an explicit confirmation gate before delegating, delegation to `git-kit:starting-work`, a read-back of what was actually created rather than assuming the request, evidence recording, and only then the Linear Started transition — in that order, per the skill's ordering requirement.

Since there's no live connectivity in this environment, nothing here reflects a real branch, a real Linear state change, or real ENG-310 content — it's a faithful simulation of what the skill would do and in what order, with plausible placeholder data standing in for what would otherwise come from live Linear/GitHub/git-kit calls.
