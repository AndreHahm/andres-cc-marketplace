# Label Taxonomy

This repository uses a structured label taxonomy to provide transparency, consistency, and professional engineering process visibility.

The goal is to make every Pull Request and Issue clearly understandable in terms of:

- **What changed**
- **Where it changed**
- **How impactful the change is**
- **How it was implemented**
- **Its lifecycle status**

---

## 1. Type (`t:`)

Describes the technical nature of the change.

- `t: bug` — A defect causing incorrect or unexpected behavior.
- `t: build` — Build system or dependency changes.
- `t: chore` — Maintenance tasks not affecting production code (repo setup, repo cleanup).
- `t: ci` — CI/CD configuration updates.
- `t: documentation` — Documentation updates or additions.
- `t: enhancement` — An improvement to existing functionality.
- `t: feature` — A new feature or capability.
- `t: performance` — Performance optimization.
- `t: refactor` — Code restructuring without changing external behavior.
- `t: security` — Security-related change or vulnerability.
- `t: test` — Adding or improving tests.

These align with Conventional Commits prefixes (`feat`, `fix`, `docs`, etc.).

---

## 2. Impact (`i:`)

Describes how strongly the change affects users or consumers.

Exactly **one** impact label is required for each Pull Request.

- `i: breaking change` — Backward-incompatible change requiring user action.
- `i: major change` — Significant change but backward compatible.
- `i: minor change` — Small change with low user impact.

Breaking changes are automatically detected from Conventional Commit titles using `!`.

---

## 3. Area / Scope (`a:`)

Describes where the change applies in the system.

- `a: ai-evals` — Evaluation/benchmarking of prompts, agents, or AI workflows.
- `a: ai-observability` — Telemetry, tracing, logging, cost/latency tracking for AI workflows.
- `a: ai-setup` — AI tooling setup: prompts, configs, agents, templates, model selection.
- `a: api` — Backend API related.
- `a: architecture` — System architecture decisions and changes.
- `a: backend` — Core backend logic.
- `a: database` — Database schema, migrations, or queries.
- `a: dependencies` — Dependency updates, lockfiles, vulnerability fixes, and transitive dependency issues.
- `a: devops` — Infrastructure, deployment, or ops.
- `a: docker` — Docker configuration and images.
- `a: frontend` — Frontend related.
- `a: github-actions` — GitHub Actions workflows, reusable workflows, and automation around Actions.
- `a: observability` — Observability: monitoring, logging, metrics, tracing, dashboards, and alerting.
- `a: tests` — Test-related area.

Scope labels make architectural boundaries visible.

---

## 4. Status (`s:`)

Describes lifecycle stage.

- `s: blocked` — Blocked by another issue, decision, or dependency.
- `s: codex review bypassed` — Marketplace CI's Codex review requirement was bypassed via a SHA-bound maintainer attestation.
- `s: do not merge` — Explicitly held back from merging regardless of check/review status.
- `s: in progress` — Currently being worked on.
- `s: merge conflict` — Has merge conflicts that need to be resolved.
- `s: needs information` — Awaiting additional information from the author.
- `s: needs review` — Awaiting reviewer feedback.
- `s: triage` — Needs initial review and classification.

---

## 5. Priority (`p:`)

Describes urgency and importance.

- `p: critical` — Top priority: requires immediate attention.
- `p: high` — High priority.
- `p: medium` — Medium priority.
- `p: low` — Low priority.

---

## 6. Execution Transparency (`x:`)

Indicates AI involvement in implementation.

- `x: ai-only` — Implemented entirely by AI (author review/merge only).
- `x: hitl` — Human-in-the-loop: AI assisted, human guided/edited/decided.
- `x: no-ai` — Implemented without AI assistance.

This ensures transparency in AI-assisted development workflows.

---

## 7. Planning (`plan:`)

Tracks planning artifacts attached to issues or PRs.

- `plan: brief` — Project brief: goals, non-goals, constraints, success criteria.
- `plan: feature` — Feature planning: breakdown, stories, acceptance criteria.
- `plan: prd` — Product requirements document.
- `plan: roadmap` — Roadmap planning: milestones, releases, timelines.
- `plan: spike` — Time-boxed research/experiment to reduce uncertainty.
- `plan: subtask` — Subtask: a granular unit of work under a `plan: task`.
- `plan: task` — Task planning: implementation plan, checklist, sequencing.

---

## 8. Automation (`auto:`)

Marks issues created automatically by repository automation, rather than by a human.

- `auto: workflow-health` — Automated workflow health alert created by `workflow-health.yml`.

---

## 9. Resolution (`r:`)

Applied when closing an issue or PR to record the outcome.

- `r: completed` — Successfully implemented.
- `r: duplicate` — Already tracked in another issue.
- `r: invalid` — Not a valid issue.
- `r: wontfix` — Will not be addressed.

---

## 10. Community/Contribution (`c:`)

Applied when communicating with contributors.

- `c: discussion` — Open discussion topic.
- `c: good first issue` — Beginner-friendly contribution.
- `c: help wanted` — Contributions are welcome.
- `c: proposal` — Proposed feature or change.

---

## Design Principles

- Labels are grouped by prefixes for clarity.
- Exactly one `i:` label is required per Pull Request.
- Multiple `a:` labels are allowed.
- Automation enforces consistency.
- The system is optimized for clarity in open-source and portfolio contexts.
