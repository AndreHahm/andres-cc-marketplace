# create-pr Dry Run — Priority Label Resolution

**Starting point (both parts):** branch `feat/example-widget`, everything already committed and
pushed, no PR open yet, no issue mentioned. User says "create a PR for this." → `create-pr` skill
activates (matches "create a PR" with no issue mentioned; `collaborating-on-a-pr` is not invoked
since no issue is named).

This is a dry run only — no Bash/git/gh/Skill/Agent calls were actually made. Everything below is a
narration of what `create-pr`'s SKILL.md (as read from
`plugins/git-kit/skills/create-pr/SKILL.md`) would do, cross-referenced against
`docs/github-label-taxonomy.md`'s Priority (`p:`) section.

---

## Part A — Bug fix: stale session token stays valid after password change

### Walkthrough of the relevant steps

1. **Pre-flight checks (steps 1–3.5):** `git status` is clean (everything already committed/pushed),
   so `commit` is not invoked. Step 3.5 (session open-issues check) finds nothing to report. Step 4
   (mandatory `cross-model-review` gate) would run against the full diff; assume for this dry run it
   returns clean or all findings are addressed, so the flow proceeds to PR creation.

2. **Step 1 (push):** already pushed, so this is a no-op confirmation.

3. **Step 2 (description):** drafted from the resolved PR template.

4. **Step 3 (draft vs. ready):** `create-pr` asks via `AskUserQuestion` — "Create this PR as a draft,
   or ready-to-merge?" Nothing in the task specifies an answer, so this walkthrough assumes the
   default, "Draft (default)," is chosen (`--draft` included below). This is an assumption, not
   something the skill would silently decide — a real run would actually stop and ask.

5. **Step 3.5 (title validation):** the title is checked against
   `scripts/marketplace_ci/pr_policy.py`'s `check_pr_title()`. A `fix(...)` type is valid. Assumed
   title: `fix(auth): invalidate session tokens on password change`.

6. **Step 3.75 (assignee):** resolved via `gh api user --jq '.login'` (falls back to the repo owner
   if that fails). For this dry run, assumed to resolve to the authenticated user's login,
   `AndreHahm` (per this session's git user).

7. **Step 3.85 (priority label — the focus of this task):** `create-pr` applies exactly one `p:`
   label per `docs/github-label-taxonomy.md`'s Priority section:
   - `p: critical` — security/data-loss risk, a broken build/CI, or something blocking an active
     release
   - `p: high` — a user-facing bug fix, or something blocking other in-progress work
   - `p: medium` — the default, unless the change itself signals a different tier
   - `p: low` — cosmetic or nice-to-have

   **Resolution: `p: critical`.** A session token that stays valid indefinitely after a password
   change is a session-invalidation vulnerability — the whole point of changing a password is to
   revoke access for anyone (including an attacker) holding the old credential/token, and this bug
   defeats that. It squarely matches the `p: critical` criterion's first listed trigger,
   "security/data-loss risk" — this isn't merely "a user-facing bug fix" (which would top out at
   `p: high`); it's a bug *whose nature is itself a security defect* (unauthorized continued access),
   which the skill's own tier ordering places above a generic user-facing bug fix. `p: medium` is
   ruled out because the change clearly signals a tier (the skill explicitly says never to default to
   medium when a signal exists), and `p: low` doesn't apply since this is neither cosmetic nor
   nice-to-have.

8. **Step 4 (marker + `gh pr create`):** the git-kit marker script runs immediately before, then the
   PR is created with every resolved flag from the steps above.

### Exact `gh pr create` command (Part A)

Using the `--body-file` form (the skill's own preferred form for "more complex PR descriptions with
proper formatting"), with the draft assumption from step 3 above:

```bash
gh pr create --draft --title "fix(auth): invalidate session tokens on password change" --body-file .github/pull_request_template.md --base main --assignee AndreHahm --label "p: critical"
```

(If the earlier `AskUserQuestion` had instead been answered "Ready-to-merge," the only change is
dropping `--draft`; every other flag, including `--label "p: critical"`, stays identical.)

---

## Part B — Small internal refactor, no user-facing change, no bug, nothing blocking

Same walkthrough through steps 1–3.75 (push already done, description drafted, draft/ready asked,
title validated as e.g. `refactor(utils): simplify helper function`, assignee resolved).

### Step 3.85 resolution for this change

Checking the same four criteria against this change:
- Not `p: critical` — no security/data-loss risk, no broken build/CI, not blocking a release.
- Not `p: high` — explicitly not a user-facing bug fix (no bug, no user-facing behavior change), and
  explicitly stated as "nothing blocking other work."
- `p: medium` is the stated default only when *nothing* signals a different tier.
- `p: low` — "a cosmetic or nice-to-have change."

**Resolution: `p: low`.** The change description matches the `p: low` criterion directly: it's an
internal restructuring with no external effect (no bug fixed, nothing else depends on it landing), which
is exactly what "nice-to-have" describes — a quality/maintainability improvement that isn't required for
anything else to function or ship. Because this is a signal the change itself clearly gives (ruling out
both `critical` and `high`, and matching `low`'s own description almost verbatim), `create-pr`'s
instruction not to "pick `p: medium` over a tier the change itself clearly signals" means the default
tier is bypassed in favor of `p: low` here, rather than falling through to `p: medium`.

The resulting flag would be `--label "p: low"` in the equivalent `gh pr create` call, with everything
else (assignee, base, title/body flags) resolved the same way as Part A.

---

## Summary

| | Nature of change | Resolved `p:` label | Why |
|---|---|---|---|
| Part A | Bug: session token stays valid after password change | `p: critical` | Session-invalidation bug = security risk, the explicit top trigger for `p: critical` |
| Part B | Small internal refactor, no behavior change, nothing blocking | `p: low` | Matches the `p: low` "cosmetic or nice-to-have" criterion directly; not a bug, not blocking, so `critical`/`high` are both ruled out |
