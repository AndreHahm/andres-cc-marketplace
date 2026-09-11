# Preparing ENG-415 for Implementation — `work-to-development` (Dry Run)

**Disclosure up front:** This environment has no live Linear, GitHub, or git-kit connectivity or credentials. Everything below follows the `work-to-development` skill's actual procedure, in its documented order, but all ticket details, search results, and git-kit outputs are **simulated placeholders**, clearly marked as such — not confirmed real facts. Nothing here should be treated as evidence that ENG-415 actually exists or that any git/Linear action actually occurred.

---

## Step 1 — Resolve context (via `linear-work-management`)

Simulated read of ENG-415:

| Field | Simulated value |
|---|---|
| Title | "Add pagination to work-item list endpoint" |
| State | Accepted |
| Outcome / acceptance criteria | Defined — 3 criteria listed (cursor-based pagination, default page size 50, backward-compat for existing callers) |
| Owner | andre.hahm@me.com (assigned) |
| Priority | Medium |
| Dependencies | None outstanding |
| Target dates | No hard due date set |
| Linked Notion rationale | One linked doc, "Pagination design notes" (simulated — not fetched, just noted as present) |

*(SIMULATED — no live Linear session; in a real run this would be an actual `linear-work-management` read.)*

## Step 2 — Confirm readiness

Dependencies: none outstanding. Acceptance criteria: present and non-contradictory. No gaps to disclose. Readiness confirmed — proceeding.

## Step 3 — Resolve policy (via `repository-gates`)

Simulated resolution: this repository's policy profile designates `git-kit` as the required provider for branch/worktree creation (matching this repo's actual `.claude/rules/route-through-git-kit-lifecycle-skills.md`, which is real and does govern this repo). No alternate provider is permitted. Policy check passes.

*(SIMULATED tool output, but consistent with this repo's real, checked-in git-kit routing rule.)*

## Step 4 — Search for existing artifacts (via `linear-github-linking`)

Simulated search across branches, commits, and PRs referencing `ENG-415`:

- **Result: None found.** No branch, commit, or PR classified as Exact/Adoptable/Conflicting/Ambiguous/Stale currently references this issue.

Since nothing was found, there's no duplicate-work risk to surface, and no adoption decision is needed.

## Step 5 — Optional transition review

This case is a single, clearly-accepted issue with no dependency exceptions, no ambiguity in the readiness check, and no existing-artifact conflict from Step 4. Per the skill's own guidance, this doesn't meet the bar for "large or ambiguous case" — so I'm **not** asking whether to dispatch `work-transition-reviewer`, and I'm disclosing that decision explicitly rather than silently skipping it. Proceeding without the optional review.

## Step 6 — Present and confirm (required checkpoint)

**Readiness summary presented to user:**
- ENG-415, Accepted, criteria defined, no blocking dependencies, no existing branch/PR found.
- Proposed request to `git-kit:starting-work`: branch name `feat/eng-415-work-item-list-pagination` (following this repo's `<type>/<linear-id-lowercase>-<slug>` convention).

**Simulated `AskUserQuestion` checkpoint** (required before invoking git-kit):

> Q: "Ready to request a new branch/worktree from git-kit for ENG-415 (`feat/eng-415-work-item-list-pagination`)? No existing artifact was found for this issue."
> Options: Yes, proceed / No, use a different branch name / Stop, I need to check something first

**Simulated answer:** "Yes, proceed."

## Step 7 — Delegate to `git-kit:starting-work`

Per the skill's own instruction, this skill never creates the branch itself and never bypasses git-kit's own checks. In a real run I would now invoke `Skill(git-kit:starting-work)` with the confirmed branch input and let it run its own sync-main, name-validation, and worktree-vs-branch confirmation.

**Simulated git-kit behavior** (not actually executed — no git-kit connectivity in this environment):
- Sync local `main` with `origin/main`.
- Validate branch name against git-kit's `[type]/[description]` convention — passes.
- Ask worktree vs. plain branch → simulated answer: **worktree**.
- Simulated result: worktree created at `.claude/worktrees/eng-415-work-item-list-pagination`, branch `feat/eng-415-work-item-list-pagination`, based off `main` at simulated SHA `a1b2c3d`.

## Step 8 — Read back what git-kit actually created

Per the skill's explicit instruction, I don't assume the request was honored exactly as asked — I read back the actual result. Simulated read-back:

- Repository: this repository (unchanged)
- Base branch: `main` (as requested — no override)
- Type: worktree (as simulated above)
- Path: `.claude/worktrees/eng-415-work-item-list-pagination`
- Branch: `feat/eng-415-work-item-list-pagination`

*(SIMULATED — using this read-back identity, not the originally-requested one, for the evidence record in Step 9, per the skill's explicit instruction.)*

## Step 9 — Record evidence (via `linear-github-linking`)

Append a `git-github-evidence` entry with `stage: "work-started"`, using the Step 8 read-back identity (not the original request):

```
stage: work-started
issue: ENG-415
branch: feat/eng-415-work-item-list-pagination
worktree_path: .claude/worktrees/eng-415-work-item-list-pagination
base: main
base_sha: a1b2c3d (simulated)
```

*(SIMULATED write — no live linking connectivity.)*

## Step 10 — Update Linear (only after Step 9's evidence is recorded)

Per the skill's Gotchas section, this Started-state transition is deliberate, not automatic, and is the only thing that changes Linear's actual workflow status (a native GitHub integration's informational branch attachment, if configured, would not substitute for this). Since Step 9's evidence write is recorded first, now transition ENG-415 to this repository's configured Started state via `linear-work-management`.

**Simulated result:** ENG-415 → "In Progress" (Started state).

## Step 11 — Read back and report

**Git identity (simulated):** worktree at `.claude/worktrees/eng-415-work-item-list-pagination`, branch `feat/eng-415-work-item-list-pagination`, based on `main`.

**Linear state (simulated):** ENG-415 moved from Accepted → In Progress, evidence entry (`work-started`) recorded before the transition.

---

**Summary:** This dry run walked ENG-415 through every step of `work-to-development` in order — context resolution, readiness confirmation, policy resolution, existing-artifact search, the (skipped, with reasoning disclosed) optional transition review, the required pre-delegation confirmation, delegation to git-kit, read-back of what was actually created, evidence recording, and finally the Linear state transition. All ticket content, search results, git-kit outputs, and the final Linear state change are **simulated** — none of this reflects real Linear, GitHub, or git state, since this environment has no live connectivity to any of those systems.
