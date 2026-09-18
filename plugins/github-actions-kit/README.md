# github-actions-kit

Generate, validate, and audit GitHub Actions workflows and custom actions. Five focused skills covering
the full lifecycle of a `.github/workflows/*.yml` file — from first scaffold through post-hoc run
diagnosis:

- **`github-actions-generator`** — scaffolds production-ready workflows and custom actions (composite,
  Docker, JavaScript) with security-hardened defaults (SHA-pinned actions, minimal permissions,
  fork-safe PR handling), auto-validating output via `github-actions-validator`.
- **`github-actions-validator`** — validates, lints, and fixes workflow/action YAML using `actionlint`
  and `act`, with a mapped error-to-reference table and a CI-pitfalls reference covering issues static
  tools miss (cache-dependency-path, monorepo build order, service-container startup).
- **`github-actions-hardening-audit`** — statically scores workflow YAML for hardening gaps: missing
  `timeout-minutes`/`permissions`/`concurrency`, floating action refs (`@main`/`@master`/`@vN`).
- **`github-actions-conclusion-audit`** — detects chronically flaky workflows from run-history JSON via
  conclusion-transition volatility scoring.
- **`github-actions-log-analyzer`** — fetches and analyzes recent workflow run logs (subagent-dispatched
  per step/skill boundary) to surface wasted effort, mistakes, and instruction-compliance gaps.

`github-actions-generator`/`github-actions-validator` are the authoring pair (generate, then validate
before shipping); `github-actions-hardening-audit`/`github-actions-conclusion-audit`/
`github-actions-log-analyzer` are the diagnostic trio (static hardening score, run-history flakiness,
raw log analysis — three different inputs over the same underlying problem: "is this CI healthy?").

This plugin does not cover non-GitHub CI platforms or deployment/infrastructure provisioning. For raw
GitHub Actions *operations* (triggering a run, watching it, downloading artifacts) rather than analysis
or authoring, see `git-kit`'s `gh-operations` skill instead.

## Installation

Install via this marketplace, or point Claude Code at this plugin directory directly for local
development:

```bash
claude --plugin-dir /path/to/andres-cc-marketplace/plugins/github-actions-kit
```

## Declared plugin language

Python. All scripts (`validate_workflow.py`, `workflow_hardening_audit.py`,
`conclusion_volatility_audit.py`, `find_step_boundaries.py`, `test-generator.py`,
`test_validate_workflow.py`) are Python, per this marketplace's `require-declared-plugin-language.md`
convention. New scripts added to this plugin should stay Python going forward.

## License

Apache-2.0.
