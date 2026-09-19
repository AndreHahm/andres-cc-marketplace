# GitHub Actions Hardening Audit — Baseline Report

Scope: `plugins/github-actions-kit/skills/github-actions-hardening-audit/fixtures/*.yml`
(3 files: `clean.yml`, `reusable-caller.yml`, `risky.yml`)

Method: manual review against general GitHub Actions security-hardening knowledge
(least-privilege `permissions:`, pinned action refs, dangerous trigger/checkout
combinations, job timeouts, secret handling). No repo-specific skill/script logic was
consulted.

## Summary verdict

| File | Risk | Notes |
|---|---|---|
| `risky.yml` | **Critical** | `pull_request_target` + no `permissions:` + floating action refs + attacker-influenced checkout |
| `reusable-caller.yml` | Low | Minor hardening gaps only; nothing exploitable found |
| `clean.yml` | None (baseline-good) | Follows hardening best practices |

---

## `risky.yml` — CRITICAL

\`\`\`yaml
name: Risky CI
on: [push, pull_request_target]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@main
      - uses: actions/setup-node@v4
      - run: echo "no permissions, no timeout, floating refs"
\`\`\`

Findings, most severe first:

1. **`pull_request_target` trigger with no `permissions:` restriction — Critical.**
   `pull_request_target` runs in the context of the base repository, which means the
   workflow's `GITHUB_TOKEN` has access to repo secrets and (by default, since no
   `permissions:` block is present) whatever broad default permissions the
   org/repo grants — potentially `write` access. Any step in this job that checks out
   or executes code influenced by the incoming pull request (which a job literally
   named `deploy` strongly suggests it will) creates a direct path for an external
   contributor to exfiltrate secrets or push malicious changes using the repo's own
   credentials. This is the single most dangerous and well-known GitHub Actions
   anti-pattern (the "pwn request" class of vulnerability) and combining it with
   the two issues below compounds the risk further.

2. **No top-level (or job-level) `permissions:` block — High.**
   Without an explicit `permissions:` block, the `GITHUB_TOKEN` falls back to the
   repository/organization default, which on many repos is still broad
   (`read/write` on contents, issues, PRs, etc.) rather than the minimal `read`
   `clean.yml` uses. Least-privilege hardening requires declaring
   `permissions: contents: read` (or narrower) explicitly, especially critical given
   the `pull_request_target` trigger above.

3. **Floating/mutable action refs — High (supply-chain risk).**
   - `actions/checkout@main` pins to a branch, not a release tag or commit SHA. A
     branch ref is mutable — whoever controls the `actions/checkout` repo (or, in a
     compromise scenario, an attacker who gains push access upstream) can change what
     code runs under this ref at any time, silently changing this workflow's behavior
     on every future run.
   - `actions/setup-node@v4` pins to a major-version tag rather than a full commit
     SHA. Tags are also mutable (can be re-pointed) and are a weaker pin than a SHA.
     `clean.yml`'s `actions/checkout@de0fac2e...  # v6.0.2` shows the correct pattern
     for comparison — pin to a full SHA with a human-readable version comment.

4. **No `timeout-minutes` — Medium (availability/cost, not directly a secret-leak
   vector).** An unbounded job can hang indefinitely, consuming runner minutes/cost
   and, in a compromised-action scenario, giving malicious code an open-ended
   execution window. `clean.yml` sets `timeout-minutes: 10`; this file sets none.

**Why this file is the highest-risk fixture:** finding #1 alone is normally sufficient
to flag a workflow as critical; here it's stacked with a missing permissions
baseline and two unpinned/floating action references, which is a textbook "everything
wrong at once" fixture — consistent with the step's own comment
(`"no permissions, no timeout, floating refs"`) essentially self-documenting the
intended defects, though it doesn't call out the `pull_request_target` issue, which is
actually the most severe finding in the file.

---

## `reusable-caller.yml` — LOW

\`\`\`yaml
name: Reusable Caller
on:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  call-shared-ci:
    uses: ./.github/workflows/shared-ci.yml
    with:
      environment: production
\`\`\`

- Declares `permissions: contents: read` at the workflow level — good, matches
  least-privilege baseline.
- Trigger is `push` to `main` only — no `pull_request_target`/`pull_request` exposure.
- Calls a **local** reusable workflow (`./.github/workflows/shared-ci.yml`) by relative
  path. Local reusable-workflow references execute at the same commit as the caller, so
  there's no separate ref-pinning concern the way there would be for a cross-repo
  `owner/repo/.github/workflows/x.yml@ref` reference — this is not a gap.
- Minor/advisory-level observations, not risky per se:
  - No `timeout-minutes` on the calling job (a reusable-workflow *caller* job doesn't
    always need one if the callee sets its own, but it's worth confirming the callee
    does).
  - Passes `environment: production` as an input with no visible approval/protection
    gating in this file — whether that's safe depends entirely on `shared-ci.yml`'s own
    contents and the target GitHub Environment's protection rules, neither of which is
    in scope here (the callee file is not among the three fixtures). This is flagged as
    **out of scope / unknown**, not as a confirmed finding.
- No secrets are explicitly passed or inherited (no `secrets: inherit`), which is
  itself a good sign — the callee only gets what its own environment/permissions allow.

Overall: no actionable hardening violation found in this file in isolation.

---

## `clean.yml` — Baseline / no findings

\`\`\`yaml
name: Clean CI
on:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2
      - run: echo "hardened workflow"
\`\`\`

This file demonstrates the hardening baseline the other two fixtures should be judged
against:
- Explicit least-privilege `permissions: contents: read`.
- Trigger scoped to `push` on `main` only (no `pull_request_target`).
- `timeout-minutes: 10` bounds job execution.
- `actions/checkout` pinned to a full commit SHA with a version comment for
  auditability/readability.

No findings.

---

## Overall ranking (riskiest first)

1. **`risky.yml` — Critical.** Ship-stopper. `pull_request_target` with no permissions
   restriction is a credential/secret-exfiltration vector; floating action refs and
   missing timeout compound the exposure.
2. **`reusable-caller.yml` — Low.** No confirmed issues in this file; one unresolved
   dependency (the callee workflow's own safety) noted as out of scope.
3. **`clean.yml` — None.** Reference-good example; nothing to fix.
