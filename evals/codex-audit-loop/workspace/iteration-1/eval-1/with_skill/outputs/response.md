Before I launch anything, I want to confirm scope and cost — this skill is explicitly the expensive, whole-project mode (3-20 parallel Codex calls per round, up to 10 rounds until convergence), not the lightweight `/codex-kit:review` path for a single PR/commit/diff.

I'd ask this now and wait for your answer:

**Which mode do you want, and are you good with the cost/scale involved?**

- **Mode A — Multi-lens checkout audit (default)**: Explore the project, derive 3-20 independent lenses covering distinct failure surfaces/subsystems, run one Codex adversarial-review per lens in parallel, synthesize and deduplicate findings, and repeat up to 10 rounds until convergence (a round adds nothing substantive, or two consecutive rounds add nothing new). Pure read/analysis — never touches the working tree, never fixes anything.
- **Mode B — Multi-branch comparison** (`--branches`): Compares named branches against a base branch. Would need the branch list and base ref.
- **Mode C — Verified fix loop** (`--mode fix`, extends Mode A): Same lens-based audit, but adds independent verification of findings, isolated fix worktrees per finding-group, and a per-group confirmed merge back. This is the most expensive and most invasive option — it's the only one that changes code.

Given your request ("full audit... across many lenses until convergence") this sounds like **Mode A**, but I want to confirm before spending the Codex call budget:

1. Confirm **Mode A** is right (report-only, no fixes) — or did you actually want Mode C (find *and* fix)?
2. Any part of the repo to exclude, or is this truly the whole project (this marketplace repo, all plugins)?
3. Are you OK with up to 10 rounds of parallel Codex calls (3-20 per round) — this can be a large number of total Codex invocations and take a while to converge?

This is the point where I'd stop and wait for your actual answer — I'm not going to assume Mode A, guess an exclusion list, or start dispatching exploration subagents or Codex calls before you respond. Once you confirm, I'll move to Mode A's Quick-Start step 2 (Explore → derive lenses → launch parallel Codex reviews → synthesize → converge) and report back what landed, what's still open, and (if Mode C) which finding-groups still need review.
