I don't have a live connection to Linear or GitHub in this environment — I can't actually read ENG-311, create a branch, open a PR, or update Linear's status. What follows is the concrete step-by-step plan I'd execute if those connections were available, with the assumptions I'm making and the checkpoints I'd confirm at each step before proceeding.

## Assumptions (stated up front, would confirm against real data)

- ENG-311 is in the Linear team whose issues map to this repo (I'd confirm which repo — a workspace can have multiple GitHub integrations attached to different teams).
- "Accepted" is this workspace's status label for "ready to be picked up" (post-triage, pre-in-progress) — I'd confirm the actual workflow state name, since "Accepted" isn't Linear's default vocabulary (default is usually Backlog → Todo → In Progress → In Review → Done).
- The issue has enough detail (description, acceptance criteria) to implement without further clarification. If it's a one-line title with no spec, I'd stop and ask rather than invent rate-limiting requirements (algorithm, scope, limits per key/IP, which endpoints, 429 response shape) unilaterally.
- No linked design doc, RFC, or existing rate-limiting middleware already exists in the codebase that this should extend rather than duplicate.
- This repo has CI configured (tests, lint) that gates PR merge.

## Step-by-step plan

**1. Pull the issue and confirm scope**
- Fetch ENG-311 (`get_issue`), read title, description, acceptance criteria, labels, linked docs/attachments, and any linked GitHub PRs/branches already present.
- Check for sub-issues or a parent issue/project — rate limiting is the kind of feature that sometimes has undocumented sibling tickets (e.g., "add rate limit headers," "add rate limit config UI") that should be sequenced or scoped out explicitly.
- Confirm: is this backend middleware only, or does it also need docs, dashboards, or client-facing error handling? If the ticket doesn't say, I'd ask rather than assume.

**2. Assign and transition the issue to "In Progress"**
- Assign to myself (or confirm who's the intended assignee — the ticket may already be pre-assigned).
- Move status from Accepted → In Progress. This is a real state transition I'd want to double check maps correctly (workspace-specific workflow states differ).

**3. Create the branch, following repo convention**
- Check the repo's branch-naming convention (e.g., `feat/eng-311-rate-limit-public-api` or whatever prefix pattern the repo's recent history uses).
- Sync local main first, branch off clean main.
- If the Linear-GitHub integration is connected, creating the branch from Linear (or naming it with the `ENG-311` token) auto-links the branch to the issue — I'd rely on that magic-word linking rather than manually pasting URLs, since it's what drives the auto-status-transition on PR open/merge later.

**4. Implement**
- Investigate the existing API framework/middleware stack first (language, framework — Express/Fastify/Django/FastAPI/etc.) to decide implementation approach: this is a "simplicity first" case — reuse an existing, well-vetted rate-limiting library appropriate to the stack rather than hand-rolling a token-bucket/sliding-window algorithm, unless the ticket specifically calls for custom behavior.
- Key open questions I'd resolve from the ticket or by asking, not by guessing: per-IP vs per-API-key limiting, limit thresholds, which routes are "public API" (all vs. a subset), response on limit exceeded (429 + Retry-After header is the standard), and whether limits are configurable per environment.
- This is a new security/traffic-control gate — before shipping it I'd want a security-focused review pass on the implementation (rate-limit bypass vectors, whether it can be starved by spoofed headers, whether it fails open or closed if the backing store — e.g., Redis — is unavailable), not just a functional review.
- Write tests: at minimum, requests under the limit succeed, requests over the limit get 429, limit resets after the window, and (if applicable) the store-unavailable failure mode behaves as intended. No behavior change ships without a test proving it.

**5. Commit**
- Stage only the rate-limiting change and its tests/docs — no unrelated cleanup.
- Conventional commit message, e.g. `feat(api): add rate limiting to public API endpoints`, referencing `ENG-311` in the body so Linear's GitHub integration links the commit.

**6. Open the PR**
- Push branch, open PR against main with a description covering: what changed, why (link ENG-311), how it was tested, and any config/env vars operators need to set.
- Include the Linear magic word in the PR description (`Fixes ENG-311` or the workspace's configured keyword) so Linear auto-transitions the issue on merge — I'd confirm the workspace's actual configured keyword/behavior rather than assume `Fixes` is wired up, since that's a per-workspace integration setting.
- If the repo has CODEOWNERS, confirm the right reviewers get auto-requested.

**7. CI and review**
- Wait for CI (tests, lint, type-check, security scan if configured) to go green. Don't request merge while red.
- Address reviewer feedback in follow-up commits, not force-pushed rewrites, unless the repo's convention is otherwise.
- Any Critical/Major review finding (especially anything touching the rate-limit bypass/failure-mode logic) gets fixed before merge, not deferred.

**8. Verify merge-readiness before merging**
- Confirm: not a draft, required checks passing, no outstanding "changes requested" reviews, and that I actually have merge rights on the repo (or the right person does).
- Confirm the merge strategy the repo uses (squash vs. merge commit) and match it.

**9. Merge**
- Merge the PR.
- Confirm the merge actually landed (not just that the merge button was clicked — check the PR shows "Merged" and main has the commit).

**10. Linear disposition**
- Confirm the issue auto-transitioned to Done via the GitHub integration. If it didn't (integration misconfigured, keyword didn't match), manually transition it and note why the automation didn't fire.
- Add a closing comment on ENG-311 linking the merged PR, summarizing what shipped (which endpoints are now rate-limited, the limits chosen, any new config), and flagging any follow-up work (e.g., "dashboard for rate-limit metrics" or "per-tenant overrides") as a new ticket rather than silently expanding this one's scope.

**11. Post-merge cleanup**
- Sync local main, delete the merged branch/worktree.
- If the change needs a deploy/release step beyond merge-to-main (this repo may or may not auto-deploy), confirm that separately — I would not mark the Linear issue "Done" if "Done" in this workspace means "live in production" rather than "merged," since those are different definitions of completion. I'd check which one applies before closing.

If you'd like, tell me the actual repo and Linear workspace conventions (branch prefix, PR-to-Linear keyword, done-means-merged-vs-deployed) and I can tighten this into an exact runbook, or execute it step by step with you supplying the Linear/GitHub outputs at each checkpoint.
