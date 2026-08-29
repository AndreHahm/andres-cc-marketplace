## Summary
A workflow's own up-front "can I run this path" dependency gate must check every dependency its later steps unconditionally invoke, not just the dependency named at the gate — an unconditional downstream call is itself an undeclared dependency if the gate doesn't also check for it.

## Environment
- **Product/Service**: `analysis-kit` plugin (source instance: `running-a-full-retrospective`'s direct-fix path)
- **Region/Version**: this repo, found during PR #108 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. A workflow offers a "direct fix" path gated on one named dependency being resolved (e.g. `git-kit`).
2. A later, unconditional step in that same path invokes a skill belonging to a *different* plugin (e.g. `Skill(plugin-rulebook)`, a `plugin-devkit` skill) that was never checked at the gate.
3. Run the workflow in a supported standalone configuration that has the gate's named dependency but not the later step's actual dependency (e.g. `analysis-kit` + `git-kit`, no `plugin-devkit`).
4. The gate passes, the direct-fix path proceeds, edits are made, and the workflow stalls mid-fix once the undeclared dependency is reached — leaving modified state behind.

## Expected Behavior
The up-front gate should check every dependency any later, unconditional step in that path will invoke — not just the one dependency the gate's own text names.

## Actual Behavior
`running-a-full-retrospective`'s direct-fix path checked only `git-kit`, while its own Step 4 unconditionally invoked `Skill(plugin-rulebook)` (owned by `plugin-devkit`) — a supported `analysis-kit`+`git-kit`-only install was offered and then stalled mid-fix.

## Impact
[Severity: Medium] The specific instance was already fixed in PR #108 (commit `4c2db7d`), requiring `plugin-devkit` resolved before offering the direct-fix path at all. This issue is about the *general* convention: no `.claude/rules/*.md` file currently states "a workflow's own dependency gate must cover every hard dependency its later unconditional steps invoke" — any other multi-step workflow with a narrow up-front gate and a later cross-plugin call could reproduce the same stall.

## Additional Context
Mined from PR #108's own review history (`chatgpt-codex-connector[bot]`; 16 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #108` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/108#discussion_r3842208251
