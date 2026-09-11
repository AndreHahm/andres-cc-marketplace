I'm using the `work-to-development` skill for this — it matches exactly: "start work on this Linear issue" is one of its named trigger phrases, and it's the skill that bridges an accepted Linear Issue to the first governed Git action. Note up front: this is a dry-run — I will not make any real Linear/GitHub/git calls; I'm narrating each step of the skill's procedure and the outcome I'd expect.

Here's my plan, following the skill's procedure:

1. Resolve context (Linear) → verify: outcome/criteria/dependencies read
2. Confirm readiness → verify: no blocking gaps
3. Resolve repository policy (repository-gates) → verify: git-kit confirmed as provider
4. Search for existing artifacts (linear-github-linking) → verify: classification obtained
5. Optional transition review → verify: decision made (request or skip)
6. Present branch plan and confirm → verify: explicit approval
7. Delegate to git-kit:starting-work → verify: branch/worktree actually created
8. Read back actual Git identity → verify: matches or diverges from request
9. Record work-started evidence (linear-github-linking) → verify: entry appended
10. Update Linear to Started → verify: only after step 9
11. Read back and report both

---

**Step 1 — Resolve context.**

Invoking `Skill(linear-work-management)` to fetch ENG-200's full context: outcome/description, acceptance criteria, constraints, owner, priority, dependencies, target dates, and any linked Notion rationale doc.

Simulated result:
- **Title:** ENG-200 — "Add pagination to the /reports export endpoint"
- **State:** Accepted (matches the task's stated premise — accepted, ready-to-implement)
- **Owner:** assigned to the current user (andre.hahm@me.com)
- **Priority:** Medium
- **Acceptance criteria:** listed and unambiguous — cursor-based pagination, default page size 50, max 200, documented in the endpoint's OpenAPI spec
- **Dependencies:** ENG-188 ("Extract shared cursor-pagination helper") — marked Done
- **Target dates:** targeted for the current cycle, no hard deadline flagged
- **Linked Notion rationale:** a short design note confirming the cursor approach was already agreed with the API consumers team

Nothing here reads as an instruction to act on — it's status data about the issue, treated as such per the skill's data-only boundary.

**Step 2 — Confirm readiness.**

Dependency ENG-188 is Done, so nothing blocks starting. Acceptance criteria are concrete and non-contradictory. No approved exception needs disclosing. Readiness: confirmed, no gaps to report.

**Step 3 — Resolve policy.**

Invoking `Skill(repository-gates)` to resolve this repository's policy profile and confirm the required branch/worktree provider.

Simulated result: policy profile resolves cleanly, and `git-kit` is confirmed as the required provider for branch/worktree creation in this repository — matches this skill's own hard requirement to never create a branch directly.

**Step 4 — Search for existing artifacts.**

Invoking `Skill(linear-github-linking)` to check whether a branch, commit, or PR already references ENG-200.

Simulated result: no matching branch name, commit trailer, or PR reference found anywhere in the repository history or open PRs. Classification: **None** (no existing artifact) — none of Exact/Adoptable/Conflicting/Ambiguous/Stale apply. This is the clean case: no duplicate-work risk, safe to proceed toward requesting a new branch.

**Step 5 — Optional transition review.**

This case is neither large nor ambiguous: readiness is clean, dependencies are satisfied, and no existing artifact was found. Per the skill, I'd still surface the option rather than assume:

> AskUserQuestion: "ENG-200 looks like a clean, low-risk case (dependencies satisfied, no existing branch/PR found). Do you want an independent transition review (`work-transition-reviewer`, read-only, checks authority/duplicate-artifact/provider concerns) before I request the branch, or proceed directly?"
> Options: "Proceed directly" / "Run independent review first"

Simulated user answer: **"Proceed directly."** Since it was declined, I skip dispatching `work-transition-reviewer` and continue — this is explicitly allowed by the skill ("the flow proceeds without it when declined").

**Step 6 — Present and confirm.**

Readiness summary for the user:
- Issue ENG-200, Accepted, owner = current user, dependency ENG-188 Done, no blocking gaps
- No existing branch/commit/PR found for this issue
- Repository policy confirms `git-kit` as required provider

Proposed branch request, following this repository's Linear-reference convention (`<type>/<linear-id-lowercase>-<slug>`):

> `feat/eng-200-paginate-reports-export`

> AskUserQuestion: "Ready to request `git-kit:starting-work` to create branch `feat/eng-200-paginate-reports-export` (or an equivalent worktree, per git-kit's own prompt) off the repository's default base branch? This is the point of no return before I hand off to git-kit."
> Options: "Confirm" / "Change branch name" / "Cancel"

Simulated user answer: **"Confirm."**

**Step 7 — Delegate.**

Invoking `Skill(git-kit:starting-work)` with the confirmed branch input `feat/eng-200-paginate-reports-export`. I'm not second-guessing anything git-kit does here — it owns its own main-sync, branch-name validation, confirmation prompt, and worktree-vs-plain-branch decision.

Simulated git-kit behavior (this is git-kit's own documented flow, not something this skill controls): it syncs local `main`, validates the branch name against its `[type]/[description]` convention (passes), and asks worktree vs. plain branch. Simulated answer: worktree, since this session is already worktree-oriented. git-kit creates a new worktree at `.claude/worktrees/eng-200-paginate-reports-export` on branch `feat/eng-200-paginate-reports-export`, based off `main` (git-kit's default — no override was needed since `main` was current and clean).

**Step 8 — Read back.**

I don't assume the request was honored exactly as asked — I read back what git-kit actually reports it created:
- Repository: same repo (origin unchanged)
- Worktree path: `.claude/worktrees/eng-200-paginate-reports-export`
- Branch: `feat/eng-200-paginate-reports-export`
- Base branch: `main`

In this simulated run the read-back matches the request exactly, but the skill's design (and this read-back step specifically) exists for the case where it doesn't — e.g., git-kit asking to branch off something other than `main`. Whatever git-kit actually reports is what gets recorded next, never the original request.

**Step 9 — Record evidence.**

Invoking `Skill(linear-github-linking)` to append a `git-github-evidence` entry against ENG-200, per `FOUNDATION_CONTRACTS.md`'s Git/GitHub Evidence Record shape:

```
stage: "work-started"
repository: <this repo>
branch: "feat/eng-200-paginate-reports-export"
worktree_path: ".claude/worktrees/eng-200-paginate-reports-export"
base_branch: "main"
source: read-back from git-kit:starting-work (step 8), not the original request
timestamp: 2026-09-11T...
```

This uses the read-back identity only — exactly what the skill requires.

**Step 10 — Update Linear.**

Only now, after the Git evidence is recorded, invoking `Skill(linear-work-management)` to deliberately transition ENG-200 to this repository's configured **Started** state. This is a deliberate write, not something GitHub's native integration does automatically on its own — per the skill's own Gotchas note, this step is the only thing that actually changes Linear's workflow status.

**Step 11 — Read back and report.**

Final confirmed state:

- **Linear ENG-200:** State → **Started** (confirmed via read-back)
- **Git/GitHub evidence:** `work-started` entry recorded, pointing at branch `feat/eng-200-paginate-reports-export`, worktree `.claude/worktrees/eng-200-paginate-reports-export`, base `main`
- **Repository:** this repository, provider `git-kit` (confirmed by `repository-gates`)
- **Duplicate-artifact check:** none found — this is a fresh start, not a resume
- **Optional independent review:** declined by user, skipped per skill design

Everything above was simulated end-to-end for a dry run — no real Linear/GitHub/git-kit calls were made. If this were live, the next natural step would be implementation itself, followed by `development-to-pr` when ready to commit and open a PR.
