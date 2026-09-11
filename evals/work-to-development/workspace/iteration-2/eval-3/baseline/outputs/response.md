I'll prepare ENG-415 for implementation the way I normally would — but I want to flag up front that this environment has no live Linear or GitHub access configured, so I cannot actually look up the real ticket. Everything ticket-specific below is illustrative/simulated, not confirmed fact. What I *did* verify for real is the state of this local repo/worktree.

---

**What I actually checked (real, not simulated):**

- Working directory: `C:\Dev\Repos\andres-cc-marketplace\.claude\worktrees\workmanagement-kit-downstream-qa`
- Current branch: `chore/workmanagement-kit-downstream-qa`
- `git status`: **not clean** — there are unstaged modifications to several files (`evals/linear-work-management/evals.json`, `evals/repository-gates/evals.json`, `evals/work-linking/evals.json`, `plugins/workmanagement-kit/FOUNDATION_CONTRACTS.md`, `plugins/workmanagement-kit/skills/linear-work-management/SKILL.md`, `plugins/workmanagement-kit/skills/work-linking/SKILL.md`) plus several untracked eval-workspace directories.

That matters immediately: this worktree is already mid-task on something else (looks like prior QA/eval work on `workmanagement-kit` itself). Before I touch anything for ENG-415, that has to be resolved one way or another — either that work gets committed/stashed properly, or ENG-415 gets its own clean branch/worktree rather than being layered on top of unrelated uncommitted changes. I would not start a new ticket's implementation on a dirty branch that's already carrying someone else's in-flight diff.

---

**What I would normally do to "prepare an accepted issue for implementation" (steps below, with simulated results clearly marked SIMULATED):**

**1. Pull the issue details from Linear.**
`SIMULATED` — no live connection, so this is illustrative only:
```
Issue: ENG-415
Title: [illustrative] "Add retry handling for X integration call"
Status: Accepted (ready for dev)
Team: ENG
Assignee: unassigned
Labels: [illustrative]
Description / acceptance criteria: [illustrative — would read in full for real]
Linked PRs/branches: none yet
```
In a real run I'd pull the full description, acceptance criteria, any linked design doc, and comment history — accepted issues sometimes have scope refinements buried in comments after the original description was written, so I'd read those too, not just the top-level description.

**2. Confirm which repo/plugin the work actually belongs to.**
Real check: this worktree is `andres-cc-marketplace`, containing `plugins/workmanagement-kit`. If ENG-415's description doesn't unambiguously point at this repo, I'd ask rather than guess — implementing against the wrong repo is expensive to unwind. (User's message says "in this repository," so I'll take that as given for this dry run.)

**3. Resolve the dirty-tree issue before branching.**
Real: I would not `git checkout -b` on top of the existing uncommitted changes without addressing them first — either confirm they're intentional in-progress work that should be committed/stashed separately, or confirm ENG-415 should get its own worktree so it's isolated from whatever's currently sitting here. Given this worktree's name (`workmanagement-kit-downstream-qa`) and the files touched (evals, SKILL.md, FOUNDATION_CONTRACTS.md), it looks like an existing QA pass in progress — not something I'd want to fold ENG-415 into.

**4. Create a properly named branch (or fresh worktree) for the ticket.**
`SIMULATED`:
```
git switch main
git pull
git checkout -b eng-415-retry-handling-x-integration
```
(Exact branch name would follow this repo's actual convention — I'd check for a `CONTRIBUTING.md`/branch-naming rule rather than invent one; nothing in what I've read here mandates a specific pattern, so the above is just illustrative.)

**5. Scope the implementation before writing code.**
- Re-read acceptance criteria as a checklist, not prose — translate each into something testably true/false when done.
- Identify the specific files/modules likely touched (grep the codebase for the relevant integration point, existing tests, related prior PRs).
- Note any ambiguity in the ticket and flag it *now*, before code, rather than guessing mid-implementation.
- Check for existing tests covering the area, and plan what new/updated tests the change needs.

**6. Update Linear to reflect work starting.**
`SIMULATED` — in a real run I'd move the issue out of "Accepted" into "In Progress" and leave a short comment noting the branch name, so anyone else looking at the ticket knows it's actively being picked up:
```
Status: Accepted → In Progress
Comment: "Starting implementation on branch eng-415-retry-handling-x-integration."
```

**7. Only then start implementing**, working against the acceptance criteria as the definition of done, and opening a draft PR early if the change is nontrivial so review can start incrementally rather than as one large diff at the end.

---

**Bottom line / what's blocking a real run right now:**

1. No live Linear/GitHub credentials in this environment — I cannot actually fetch ENG-415's real title, description, or acceptance criteria. Everything issue-specific above is a placeholder shape, not real ticket content.
2. This worktree currently has uncommitted, unrelated changes on `chore/workmanagement-kit-downstream-qa` — that needs to be resolved (committed, stashed, or left alone in favor of a fresh branch/worktree for ENG-415) before any real implementation branch gets created here.

If you can get me live Linear access (or paste the issue's title/description/acceptance criteria directly), I can turn step 5 into an actual concrete implementation plan against this repo's real code instead of a placeholder.
