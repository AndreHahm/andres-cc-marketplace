# Sonar Mechanisms

The rungs, decision rights and classification mapping for a `sonar` record, read from `SKILL.md`'s
"Sonar mechanisms" section. Everything here is part of the skill's procedure, not background.

For a `sonar` record, steps 1 to 6 apply with these mechanisms. Severities are verbatim (`BLOCKER`, `CRITICAL`,
`MAJOR`, `MINOR`, `INFO`), and `VULNERABILITY` counts as the `Security` category.

| Rung | Mechanism |
|---|---|
| 1. Fix in code | The same |
| 2. Inline suppression | Python files only: `# NOSONAR(<key>)`, where `<key>` is the finding's own `rule` without its `python:` prefix (for `python:S5655`, `# NOSONAR(S5655)`), plus the reason on that line (`references/suppression-formats.md`). No other language's form is verified, so a finding in any other file skips rung 2. `S1309` (the rule that tracks suppressions) cannot be suppressed this way, so it skips rung 2 too |
| 3. Per-issue transition | `sonar api post /api/issues/do_transition`, `falsepositive` or `accept`, with a comment (`references/ignore-reasons.md`) |
| 4. Path exclusion | A project setting in the UI, Administration → Analysis Scope → Ignore Issues on Multiple Criteria, not `.sonarcloud.properties` (per SonarSource staff on its community forum, checked 2026-11-08: multi-value settings are set only in the UI, and the documented `.sonarcloud.properties` settings include none). Handed to the user |
| 5. Gate or profile change | Handed to the user; `using-sonarqube-cloud` covers how |

| Action | Who decides |
|---|---|
| Rung 1, any severity | Decided and disclosed; the count must be proven to drop |
| Rung 2 in a Python file on `MINOR` or `INFO`, not `VULNERABILITY`; or on `MAJOR` for a shape `docs/ci.md` records as accepted. Neither may carry a `SECURITY` impact or a `HIGH` or `BLOCKER` impact | Decided and disclosed, with the reason written in the comment |
| Rung 2 in a Python file on any other finding, on any finding with such an impact, or a name not listed here | `AskUserQuestion`, once per finding or per named group |
| Rung 3, any severity | `AskUserQuestion` per command, as for Codacy: its exact text, reason and comment per approval, after the fresh re-collect in step 1. Always a remote write. Before running the approved command, re-read the head with `python3 -I ${CLAUDE_PLUGIN_ROOT}/skills/resolving-analysis-findings/scripts/read_pr_head.py <owner/repo> <pr>`; if it differs from the re-collected record's `source.head_commit_sha`, re-collect and ask again; on any non-zero exit, stop. The head check cannot see someone else changing the issue meanwhile, so also re-read the issue's own state right before the command, with `python3 -I ${CLAUDE_PLUGIN_ROOT}/scripts/qlty-sonar-read.py issue-state --issue <issue_id>` (pre-approved; on a non-zero exit, stop): if its `issueStatus` is no longer `OPEN` or `CONFIRMED` (for `reopen`, no longer the record's `ignore_reason`), re-collect, show the current state and ask again. If the transition is refused anyway, do the same, and never retry the same command. `reopen` needs the same approval |
| Rung 4 | Not run here: give the user the exact rule key and path pattern to enter, and what the path stops being reported for |
| Rung 5, bulk transitions, `sonar remediate` | Not run here: give the user the exact change |

Classify as in "Real or false positive": `FalsePositive` maps to the `falsepositive` transition, and
`NotExploitable`, `AcceptedUse`, `TestCode` and `ExternalCode` to `accept`, with the classification stated in the
comment. A name a framework requires is `AcceptedUse`, not `FalsePositive`: the rule read the name correctly.
Verify reads the `sonar` record the same way, and Sonar's own issue list (read through the collector) is the authority. If Sonar did not
honor a `NOSONAR`, fall back to rung 3 and say so. Rung 4 applies from the next analysis after the user sets it: re-collect then, and say when it was not yet re-analyzed.
