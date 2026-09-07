# GitHub Label Usage Guide

This document describes how labels are applied and enforced in Pull Requests.

---

## Automatic Labeling

Pull Requests are automatically labeled based on their Conventional Commit title.

Examples:

- `feat(api): add endpoint`
  → `t: feature`
  → `s: needs review`

- `build(deps): bump Newtonsoft.Json`
  → `t: build`
  → `a: dependencies`
  → `s: needs review`

- `feat!: redesign API contract`
  → `t: feature`
  → `i: breaking change`
  → `s: needs review`

---

## Impact Label Enforcement

Each Pull Request must have **exactly one** of:

- `i: breaking change`
- `i: major change`
- `i: minor change`

If none or more than one are set, CI will fail.

Breaking changes are automatically detected from `!` in the commit title and enforced.

---

## Manual Labeling Guidelines

### When to use `i: major change`

- Significant refactoring
- Architectural restructuring
- Large new features

### When to use `i: minor change`

- Small features
- Bug fixes
- Documentation updates
- Small refactors

---

## Dependencies

Use `build(deps):` or `chore(deps):` for dependency updates.

This automatically applies:

- `a: dependencies`

---

## Observability

Use `a: observability` for:

- Metrics
- Logging
- Tracing
- Monitoring
- Dashboards
- Alerting rules

---

## GitHub Actions

Use `a: github-actions` for:

- Workflow logic
- Reusable workflows
- Release automation
- CI enhancements
- Labeling automation

---

## AI Transparency

Choose exactly one execution-transparency label:

- `x: ai-only` — contribution is entirely AI-generated
- `x: hitl` — AI assisted; a human reviewed and directed the work
- `x: no-ai` — implemented without any AI assistance

This supports transparent AI-assisted development practices.

---

## Size Labels

Size labels reflect the total lines changed (additions + deletions) in a Pull Request, kept in sync
automatically by `pr-size-labeler.yml` on every push to the PR — never applied or removed manually.

- `size: XS` — <10 lines changed
- `size: S` — 10-49 lines changed
- `size: M` — 50-249 lines changed
- `size: L` — 250-999 lines changed
- `size: XL` — >=1000 lines changed

Only one size label is active at a time; the workflow removes any stale size label when the diff
shrinks or grows into a different bucket.

---

## Status Labels

Status labels reflect the current lifecycle stage of an issue or PR.

- `s: triage` — apply to newly opened issues awaiting initial classification
- `s: needs information` — apply when more context is required from the author before action can be taken
- `s: in progress` — apply when work has actively started
- `s: needs review` — apply to PRs awaiting reviewer feedback
- `s: blocked` — apply when progress is blocked by an external dependency, decision, or another issue

Only one of these five lifecycle-status labels should be active at a time. Update it as the issue or
PR progresses.

The remaining `s:` labels — `s: merge conflict`, `s: do not merge`, and `s: codex review bypassed` —
are orthogonal state flags, not lifecycle stages: each can coexist with any one lifecycle-status label
above (e.g. a PR can be `s: needs review` and `s: merge conflict` at the same time), and applying one
never removes or replaces the current lifecycle status.

---

## Planning Labels

Planning labels mark issues or PRs that carry a specific planning artifact.

- `plan: brief` — attach to issues scoping a new project (goals, non-goals, constraints)
- `plan: prd` — attach when a product requirements document is linked or embedded
- `plan: feature` — attach to feature breakdown issues (stories, acceptance criteria)
- `plan: task` — attach to implementation checklists or task-level planning
- `plan: roadmap` — attach to milestone or release planning issues
- `plan: spike` — attach to time-boxed research or investigation issues

---

## Resolution Labels

Resolution labels are applied only when closing an issue or PR to record the outcome.

- `r: completed` — successfully implemented and merged
- `r: duplicate` — already tracked in another issue; link the original before closing
- `r: invalid` — not a valid issue or out of scope
- `r: wontfix` — acknowledged but will not be addressed; add a comment explaining why

---

## Philosophy

The labeling system exists to:

- Improve clarity
- Enforce engineering discipline
- Make architectural decisions visible
- Demonstrate process maturity
- Support open-source collaboration
- Provide portfolio transparency

Consistency matters more than perfection.
