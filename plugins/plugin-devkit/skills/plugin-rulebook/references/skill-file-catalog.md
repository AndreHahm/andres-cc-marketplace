# Skill File Catalog

Full index of every resource this skill ships or reads — extracted from `SKILL.md`'s own "Reference
Guide" section per `references/adding-a-new-rule.md`'s line-budget step, to keep `SKILL.md` itself under
its own R13 threshold as new rules (R28-R32) were added.

| Resource | Purpose |
|---|---|
| `${CLAUDE_SKILL_DIR}/assets/settings.json` | Active rule configuration (plugin-portable defaults) — read this first on every invocation |
| `{REPO_ROOT}/.claude/plugin-rulebook.config.json` | Repo-specific R23 whitelist/blacklist/excluded_paths override — read second, if present (see "Repo-Specific Configuration" in `SKILL.md`) |
| `{REPO_ROOT}/.claude/plugin-rulebook-audit-decisions.md` | This repo's own Upstream Audit decision log (moved out of the plugin package — see "Repo-Specific Configuration" in `SKILL.md`) |
| `${CLAUDE_SKILL_DIR}/references/repo-specific-configuration.md` | Full load procedure and rationale for the repo-config split, expanded from "Repo-Specific Configuration" in `SKILL.md` |
| `${CLAUDE_SKILL_DIR}/references/adding-a-new-rule.md` | Checklist of every location a new rule (RNN) touches — SKILL.md sections, settings.json, the R20 sibling sweep, and mirroring — read before adding a rule |
| `${CLAUDE_SKILL_DIR}/references/size-rules.md` | R13/R18/R21 tiered thresholds for line count, code block size, and description size |
| `${CLAUDE_SKILL_DIR}/references/argument-consistency.md` | R22 detection procedure and worked examples for argument-hint/arguments consistency |
| `${CLAUDE_SKILL_DIR}/references/naming-conventions.md` | Full naming rules with examples for all component types |
| `${CLAUDE_SKILL_DIR}/references/formatting-rules.md` | Detailed formatting requirements and anti-patterns |
| `${CLAUDE_SKILL_DIR}/references/language-rules.md` | Language requirements, lang codes, multilingual variant procedure |
| `${CLAUDE_SKILL_DIR}/references/external-reference-policy.md` | R23 detection procedure, whitelist/blacklist matching, marketplace.json auto-allow, worked examples |
| `${CLAUDE_SKILL_DIR}/references/plugin-file-surface.md` | Shared plugin-scope/CWD-scope file-enumeration definition used by `language-reviewer`, `external-references-reviewer`, `consistency-reviewer`, `completeness-reviewer`, and `scripts-reviewer` — load together with the row below |
| `${CLAUDE_SKILL_DIR}/references/gitignore-exclusion.md` | Shared procedure, used by every reviewer agent, for excluding gitignored paths before reviewing Glob results (including the enumeration the row above defines) — and the companion authoring-side rule that no component may reference a gitignored path as a live dependency |
| `${CLAUDE_SKILL_DIR}/references/overhead-and-cost-rules.md` | R25/R26 violations, fix guidance, and worked examples |
| `${CLAUDE_SKILL_DIR}/references/compact-rule-checklist.md` | Pattern/violation/severity table for all enabled rules, no narrative — read by the `plugin-rulebook-checker` agent instead of this file, to avoid re-reading full teaching prose on every isolated/backgrounded dispatch |
| `${CLAUDE_SKILL_DIR}/references/allowed-languages.md` | R24 full whitelist/banned/exempt lists, worked violation examples, and fix guidance |
| `${CLAUDE_SKILL_DIR}/references/suggested-additional-rules.md` | R11/R12/R15/R16 — disabled-by-default rules and why each might be worth enabling |
| `${CLAUDE_SKILL_DIR}/references/branch-and-pr-preflight.md` | Open-PR check and Branch-scope check procedures. **Hosted here, not consumed by this skill's own Compliance Check Procedure** — `plugin-lifecycle-upstream`, `plugin-lifecycle-downstream`, and `plugin-lifecycle-maintenance` are the three actual readers of this file; `plugin-rulebook` just ships it since it lives inside this skill's own `references/` directory |
| `${CLAUDE_SKILL_DIR}/references/open-item-discipline.md` | Phase-Completion check, Pre-Commit Disclosure, and downstream's proactive offer — shared by all three lifecycle skills |
| `${CLAUDE_SKILL_DIR}/references/frontmatter-corrections.md` | R5's `AskUserQuestion`/non-functional-field corrections, R6's agent-file Bash-scoping exception and full scope/verdict table |
| `${CLAUDE_SKILL_DIR}/references/evidence-schema.md` | Shared scope-manifest/finding/report-revision/evidence-bundle shapes used across `plugin-lifecycle-downstream`'s twelve-phase pipeline; validated by `scripts/validate_evidence.py` |
| `${CLAUDE_SKILL_DIR}/references/deep-test-coverage.md` | Which component types (skill/agent/hook) have a real Deep Test path today and which (command/rule) don't yet — and how to report a `skipped` type without omitting it |
| `${CLAUDE_SKILL_DIR}/references/finding-id-fix-contract.md` | Shared bounded-finding-ID fix contract for the five dev skills and `skill-improver-loop` — input/output shape, never-self-verify rule, `skill-improver-loop`'s own attempt-count and two-valid-paths rules |
| `${CLAUDE_SKILL_DIR}/references/testing-mandate-rules.md` | R28-R31 full check procedures, config shapes, and source verification |
| `${CLAUDE_SKILL_DIR}/references/data-only-boundary.md` | R32 canonical wording, the three required elements, and the full check |
| `${CLAUDE_SKILL_DIR}/scripts/mirror-parity-check.sh` | CI-owned, not invoked from within this skill's own Compliance Check Procedure — confirmed consumer is `.github/marketplace-validators.json`'s `plugin-devkit.mirror-parity-check` entry, not an agent-driven check, so it carries no `allowed-tools` Bash grant here |
| `${CLAUDE_SKILL_DIR}/scripts/r20-sweep.sh` | Automates the R20 sibling sweep's repo-wide grep for a stale rule-count-ceiling mention — see `references/adding-a-new-rule.md`'s Touch List |
| `${CLAUDE_SKILL_DIR}/scripts/check_tool_grants.py` | Mechanical backing check for R6's "Tool completeness" sub-rule — flags a body command span with no matching `Bash(<prefix>:*)` grant; full-file heuristic, not a diff, see its own docstring for known false-positive classes |
| `${CLAUDE_SKILL_DIR}/scripts/agent-cost-tracker.py` | Reads/updates `assets/agent-cost-history.json` — gives R26's `AskUserQuestion` gate a real cost figure to cite when historical data exists; see `references/overhead-and-cost-rules.md`'s "Cost-Tier Estimation Before Dispatch" |
| `${CLAUDE_SKILL_DIR}/assets/agent-cost-history.json` | Best-effort registry of observed `Agent()` dispatch cost (tokens, duration), read/written by `scripts/agent-cost-tracker.py` |
| `${CLAUDE_SKILL_DIR}/scripts/validate_evidence.py` | Validates a YAML/JSON document against `references/evidence-schema.md`'s manifest/finding/report/bundle shapes — invoke as `python scripts/validate_evidence.py <shape> <path>`, or `--self-test` |
| `${CLAUDE_SKILL_DIR}/references/compliance-report-example.md` | Full worked example of the Compliance Check Procedure step 7 output shape |
