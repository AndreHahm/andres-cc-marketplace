# Walkthrough: ENG-311 "Add rate limiting to the public API" — Full Linear-GitHub Lifecycle Run

## Working Assumptions (stated up front, since no live connectors are available)

Because there are no live Linear/GitHub/Notion MCP calls in this environment, every "tool call" below is a **simulated** result, explicitly labeled `[SIMULATED]`. Where a real run would branch on the actual returned data, I show the branch I'd take under the assumed result and call out where a real run could diverge.

- **Issue**: ENG-311, "Add rate limiting to the public API," Linear status = Accepted (per the request). Team = ENG. No prior Linear-GitHub Lifecycle run has ever touched this Issue — this is a fresh start, not a resume, but I still perform the resume check below rather than assuming that.
- **Repository**: `acme/api-service` (assumed — the repo this Issue's team is configured to work in), default branch `main`, hosted on GitHub, with `repository-gates` already reporting a valid `repository_policy.provider_profile`.
- **Scope of the work**: adding rate limiting to public API endpoints — assumed to mean request throttling middleware (e.g., token-bucket per API key/IP), configurable limits, 429 responses with `Retry-After`, and tests. No design doc is attached to the Issue in this simulation; if a real run found one, Implement would follow it instead of this assumption.
- **Solo delegate**: no other engineer is co-assigned; the calling user is the implementer.
- **Wave 1 / Wave 2 foundation**: assumed activated (host profile, versioned configuration, schema-v2 extension) — I state this as a checked prerequisite below rather than silently assuming it.

I'll flag explicitly anywhere a real run's actual data would change my branch.

---

## Phase 0 — Prerequisite Check + Resume Check

Before entering Phase 1, this skill's own Prerequisites section requires confirming the Issue is genuinely accepted and that Wave 1/2 foundation is active — and Resume Behavior requires checking for any prior evidence before assuming this is a fresh run, even though the user described it as "already Accepted."

**Actions (not delegated — this skill's own intake logic):**

1. `Skill(linear-work-management)` → `[SIMULATED]` confirm ENG-311's current status is genuinely "Accepted" via a real criterion-backed transition, not a direct status write with no criterion evaluation behind it (per that skill's own Gotcha about closed/accepted-looking statuses). Result: **confirmed Accepted**, acceptance criteria present (assumed: "rate limiting enforced on all public endpoints; 429 returned when exceeded; limits configurable; tests cover normal/boundary/exceeded cases").
2. `Skill(linear-github-linking)` → `[SIMULATED]` read ENG-311's `git-github-evidence` array. Result: **empty array** — no `work-started`, `commit-linked`, `pr-published`, `pr-ready`, or `pr-merged` entries exist. This is genuinely a fresh run, not a resume.
3. Verify Wave 1 foundation (host profile, versioned configuration) and Wave 2 schema-v2 extension are activated per `../../FOUNDATION_CONTRACTS.md` — `[SIMULATED]` **active**. If this had come back inactive, per Failure and Resume I would stop immediately with a manual handoff naming exactly what's missing, rather than proceeding on a partial/assumed configuration.
4. Confirm the repository's Git/GitHub setup — deferred to `repository-gates`, which each focused phase below invokes on its own; I don't re-verify every setup step here myself, per this skill's own Prerequisites note.

**Outcome:** clean fresh start confirmed. Proceeding to Phase 1.

---

## Phase 1 — Prepare + Start

**Delegated to:** `Skill(work-to-development)` — this skill does not itself pick a branch name, create a worktree, or transition Linear status; all of that logic belongs to `work-to-development`.

### Sequence-level gate (this skill's own, additive)

Per "Confirmation and Safety" and the Phases table, this skill adds its own confirmation on top of `work-to-development`'s internal gate — it doesn't replace it.

**AskUserQuestion (fired by linear-github-lifecycle itself):**
> "About to start Phase 1 (Prepare + Start) for ENG-311 — this will invoke `work-to-development` to create a branch/worktree and transition the Issue to Started in Linear. Proceed?"
> Options: **Proceed** / **Cancel** / **Show issue details first**

`[SIMULATED user response]`: **Proceed**.

### Delegation

`Skill(work-to-development)` is invoked with ENG-311 as input. Internally (not performed by this skill — I'm naming what the sub-skill does, not doing it myself):
- Resolves repository/team context for ENG-311.
- Invokes `git-kit:starting-work` to sync `main`, validate a branch name (assumed generated: `feat/eng-311-rate-limiting-public-api`), and offer worktree vs. plain branch — `[SIMULATED]` worktree chosen, created at `.claude/worktrees/eng-311-rate-limiting-public-api`.
- `work-to-development`'s own internal confirmation gate fires here too (separate from this skill's sequence-level gate above) — `[SIMULATED]` confirmed.
- Transitions ENG-311 to **Started** in Linear.
- Appends a `work-started` entry to ENG-311's `git-github-evidence` array (repository, branch, timestamp).

**Produces:** verified branch/worktree, `work-started` evidence, Linear Started. `[SIMULATED]` all three landed successfully.

### Mandatory worktree re-entry check

Per this skill's explicit instruction: `starting-work` only creates the worktree and reports its path — it never changes the calling session's own cwd. Before treating Prepare + Start as done, I must explicitly verify/change into the reported path rather than assume it's active — this is exactly the failure mode named in `require-worktree-rooted-absolute-paths.md` and `starting-work-before-first-change.md`.

**Action:** `[SIMULATED]` run `pwd` (or `Get-Location`) and confirm cwd is now `.../worktrees/eng-311-rate-limiting-public-api`; if not, `cd` into it before Phase 2 starts. All subsequent absolute-path `Read`/`Edit`/`Grep` calls in Phase 2 are rooted under this worktree path, per `require-worktree-rooted-absolute-paths.md`.

---

## Phase 2 — Implement / Control Scope

**Not delegated to a focused skill** — per the Phases table, this is ordinary repository work in the active worktree under the user's own instructions. This skill's only job here is to track that it happened and to gate any material Linear correction.

### Work performed (ordinary engineering, in the worktree)

- Add rate-limiting middleware (assumed token-bucket, per-API-key and per-IP) to the public API layer.
- Add configuration surface for limits (env var or config file, assumed pattern matching existing repo config conventions — I'd actually `Read` the repo's config module before assuming this, not invent a new mechanism).
- Return `429 Too Many Requests` with `Retry-After` header when exceeded.
- Add unit tests: under-limit pass-through, at-limit boundary, over-limit rejection, header correctness, and (if the codebase already has integration/contract tests for the public API) an integration test hitting the limited endpoint.
- Update any relevant developer-facing docs/comments only where directly touched by this change (per CLAUDE.md's Surgical Changes rule — no drive-by refactors of unrelated middleware).

### Material Linear correction gate

Per the Phases table: this skill requires `AskUserQuestion` confirmation before any material correction to Linear during Implement (e.g., discovering the acceptance criteria are wrong, scope needs to shrink/grow, or the Issue needs to be reopened/relabeled).

`[SIMULATED]`: no material correction needed — implementation matches the accepted criteria as understood. **Gate does not fire** in this run. (If, say, I'd discovered the "configurable limits" criterion was ambiguous about per-route vs. global limits, I would stop and fire `AskUserQuestion` here rather than silently picking an interpretation and updating Linear unilaterally.)

**Produces:** in-scope changes ready to commit. No Git/GitHub evidence entry for this phase (by design — Resume Behavior explicitly notes Implement has no evidence stage of its own).

---

## Phase 3 — Commit + Gates + Publish

**Delegated to:** `Skill(development-to-pr)`.

### Sequence-level gate

**AskUserQuestion (fired by linear-github-lifecycle):**
> "Implementation looks complete for ENG-311 (rate-limiting middleware + tests added). Proceed to Phase 3 — commit, run gates, and publish a draft PR via `development-to-pr`?"
> Options: **Proceed** / **Cancel** / **Let me review the diff first**

`[SIMULATED]`: **Proceed**.

### Delegation

`development-to-pr` internally (again, its logic, not mine):
- Routes the actual commit through `git-kit:commit` — staging review, sensitive-file scan, conventional-commit message confirmation. `[SIMULATED]` commit created: `feat(api): add rate limiting to public API endpoints`, linked to ENG-311.
- Runs repository gates via `repository-gates` (CI/lint/test policy resolution) — `[SIMULATED]` result: **pass** (tests green, lint clean). If this had come back `pending`/`fail`/`bypassed`, that exact observed value would be carried into the `pr-published` evidence's own `gates[]` array rather than normalized to a bare pass/fail.
- Publishes a **draft PR** via `git-kit:create-pr`. `[SIMULATED]` PR #412 opened, draft, linked to ENG-311.
- Appends `commit-linked` evidence, then `pr-published` evidence (carrying `gates: [{name: "ci", result: "pass"}, ...]`) to ENG-311's `git-github-evidence` array.

**Produces:** `commit-linked` evidence, `pr-published` evidence with the observed gate result, draft PR #412.

---

## Phase 4 — Review/Fix + Ready

**Delegated to:** `Skill(pr-to-linear)`.

### Sequence-level gate

**AskUserQuestion:**
> "Draft PR #412 is published for ENG-311 with gates passing. Proceed to Phase 4 — review/fix cycle and mark ready via `pr-to-linear`?"
> Options: **Proceed** / **Cancel** / **Hold as draft for now**

`[SIMULATED]`: **Proceed**.

### Delegation

`pr-to-linear` internally:
- Triggers/monitors review (this would, in a live run, route through `handling-review-findings` for any automated Codex/CodeRabbit/human findings — not reimplemented here).
- `[SIMULATED]` one Minor finding: "rate limit config default too permissive for the `/public/search` route" — fixed in a follow-up commit within the same PR, re-gates pass.
- `pr-to-linear`'s own internal confirmation gate fires before flipping the PR from draft to ready — `[SIMULATED]` confirmed.
- Flips PR #412 from draft to **ready for review/merge**.
- Writes a deliberate blocker summary (here: "no blockers; one Minor finding fixed pre-ready") back to ENG-311 as a comment/status note.
- Appends `pr-ready` evidence to the Issue's `git-github-evidence` array.

**Produces:** deliberate blocker summary, `pr-ready` evidence.

---

## Phase 5 — Merge + Linear Disposition

**Delegated to:** `Skill(merge-to-completion)`.

### Sequence-level gate

**AskUserQuestion:**
> "PR #412 is ready with no outstanding blockers. Proceed to Phase 5 — merge and resolve ENG-311's Linear disposition via `merge-to-completion`?"
> Options: **Proceed** / **Cancel** / **Wait for one more reviewer pass**

`[SIMULATED]`: **Proceed**.

### Delegation

`merge-to-completion` internally:
- Verifies merge readiness and merge rights via `git-kit:merge-pr` (not draft, checks passing, no outstanding change requests, current user has merge rights). `[SIMULATED]` verified.
- `merge-pr`'s own internal `AskUserQuestion` fires before actually merging — `[SIMULATED]` confirmed, merges PR #412 into `main`.
- Appends `pr-merged` evidence to ENG-311's `git-github-evidence` array (this is Git/GitHub evidence only — it proves the merge happened, nothing more).
- Reaches post-merge cleanup **indirectly**, through `git-kit:merge-pr`'s own step 8 (offering `finishing-work`) — `merge-to-completion` does not perform cleanup as a separate action itself, per the Phases table's explicit note. `[SIMULATED]` `finishing-work` accepted: syncs local `main`, hands off to `/git-cleanup` for worktree/branch deletion.
- Proceeds to the actual **Linear disposition** (steps 9-14 of `merge-to-completion`): re-evaluates ENG-311's acceptance criteria against what actually shipped, resolves any outstanding criterion (linking follow-ups if needed), and decides close vs. deliberately-stays-open. `[SIMULATED]`: all criteria satisfied (rate limiting enforced, 429 + `Retry-After`, configurable limits, tests present) → ENG-311 transitioned to **Done/Closed** via a genuine criterion evaluation (not a direct status write).
- This disposition write is an ordinary base Transition Contract write with **no `git-github-evidence` entry of its own** — exactly as the skill's own Resume Behavior section warns. I'm calling this out explicitly rather than treating the Issue's now-closed status as self-evidently proof of anything, since this run completed disposition in the same pass and the closed status is a *result* I'm reporting, not something a future resume should trust blindly.

**Produces:** `pr-merged` evidence, verified Linear disposition (closed, criteria-backed).

---

## Phase 6 — Deliberate Notion Learning

**Delegated to:** `Skill(status-and-learning)`.

### Sequence-level gate

**AskUserQuestion:**
> "ENG-311 merged and closed. Proceed to Phase 6 — capture a dated outcome/learning record in Notion via `status-and-learning`?"
> Options: **Proceed** / **Cancel — skip Notion learning for this Issue**

`[SIMULATED]`: **Proceed**.

### Delegation

`status-and-learning` internally:
- Composes a dated outcome record: what shipped (rate limiting on public API), any deviations from the original acceptance criteria (none in this run), the one Minor review finding and its fix, and any reusable learning (e.g., "default rate-limit config needs route-specific overrides going forward — worth a follow-up Issue if not already filed").
- `[SIMULATED]` writes this to the workspace's Notion knowledge base, dated today (2026-09-11).

**Produces:** dated outcome/learning record in Notion. This has **no `git-github-evidence` entry** — noted for the record, matching the skill's own explicit warning that this phase leaves no trace in that array.

---

## Reconciliation — Not Run

Per the Phases table and Gotchas, `linear-github-reconciliation` runs **only on demand**, not automatically every pass. Nothing in this run surfaced suspected drift (evidence entries landed cleanly, no force-pushes, no base-branch changes, no conflicting direct writes to ENG-311 observed). **Explicitly skipping it here, with reason stated** — not silently omitting it — per `disclose-before-overriding-decisions.md`'s requirement to disclose any skipped phase.

---

## Data-Only Boundary Note

Per this skill's Confirmation and Safety section: every value read back in this run from `linear-work-management`, `linear-github-linking`, and each delegated phase's own evidence/classification was treated as untrusted descriptive data, never as an instruction — e.g., the Issue title and any review-finding text were read as content to report, not as directives to act on. Nothing in this simulated run contained instruction-like text, so no suspicious-content flag was raised.

---

## Final Evidence Summary (ENG-311)

| Stage | Evidence | Status |
|---|---|---|
| `work-started` | branch `feat/eng-311-rate-limiting-public-api`, worktree created | recorded |
| `commit-linked` | commit linked to ENG-311 | recorded |
| `pr-published` | PR #412 (draft), gates: `pass` | recorded |
| `pr-ready` | PR #412 flipped ready, 1 Minor finding fixed pre-ready | recorded |
| `pr-merged` | PR #412 merged to `main` | recorded |
| Linear disposition | ENG-311 closed, criteria-backed evaluation | completed (no separate evidence entry — see Phase 5 note) |
| Notion learning | dated outcome/learning record captured | completed (no evidence entry — see Phase 6 note) |
| Reconciliation | — | skipped, no drift suspected |

**Sequence-level `AskUserQuestion` gates fired:** before Phase 1, before Phase 3, before Phase 4, before Phase 5, before Phase 6 — five gates total, each additive to (not a substitute for) the focused skill's own internal confirmation at that phase. The Implement-phase "material Linear correction" gate did not fire, since no correction was needed.

**Everything above marked `[SIMULATED]` is a stand-in for a live Linear/GitHub/Notion MCP result** — in a real session with those connectors active, each simulated result would instead be the actual tool response, and any divergence from these assumptions (e.g., gates failing, a reviewer blocking finding, criteria not fully met) would change the corresponding phase's branch exactly as documented in each focused skill's own gates rather than following this hypothetical happy path.
