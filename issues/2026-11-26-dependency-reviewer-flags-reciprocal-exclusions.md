## Summary
dependency-reviewer reports reciprocal When NOT to Use routing exclusions, which R36 asks for, as blocking "bidirectional dependency" findings.

## Environment
- **Product/Service**: plugin-devkit `dependency-reviewer` agent, run as a Codex export by CI's `Codex delta review` job
- **Region/Version**: `main` at 008d9bf6; Codex model gpt-6-luna, CLI pin 0.170.0
- **Browser/OS**: n/a

## Reproduction Steps
1. Add a `## When NOT to Use` section to a skill that names a sibling skill for a task it does not own (for example git-bisect: "Adding metadata to a commit is `git-notes`' job").
2. Have the sibling name the first skill back for its own half of the boundary, as R36 and `.claude/rules/resolve-activation-overlap-bidirectionally.md` ask.
3. Open a PR; CI's `Codex delta review` runs dependency-reviewer over the diff.

## Expected Behavior
No dependency finding: neither skill calls the other. dependency-reviewer's own definition of a bidirectional dependency is "two components that each declare a `Skill()`/`Agent()` call to the other" (`plugins/plugin-devkit/agents/dependency-reviewer.md`, Step 3), and a routing exclusion is not a `Skill()` call.

## Actual Behavior
Found in PR #920 (head b2c476217eed24e990089071a092bad858306f42), CI run 45812663080: dependency-reviewer raised six blocking Major `dependency-graph` findings, one per reciprocal pair, each stating that "whether runtime routing can nest is unverified; the documented edges form a bidirectional dependency":

- gh-operations and collaborating-on-a-pr
- gh-operations and codex-review-recovery
- gh-operations and github-issue-lifecycle
- gh-operations and github-issue-creator
- manage-codeowners and merge-pr
- git-notes and git-bisect

The same run's deterministic `call-graph` verifier was clean. The local CI-parity run on the same diff raised the same pattern once, for git-notes and git-bisect.

## Error Details
~~~
Major dependency-graph plugins/git-kit/skills/git-notes/SKILL.md:42
Remediation: Break the cycle by removing one direct routing edge, or gate the two invocations so they cannot nest in one run.
~~~

## Visual Evidence
n/a (findings are in the CI job's result JSON).

## Impact
Medium: every PR that adds R35 When NOT to Use sections with R36-style reciprocal exclusions, which is the whole #461 plan, is blocked by a finding that contradicts the reviewer's own definition. The only ways through are rewording or waiver lines, PR after PR. Removing one edge, as the remediation suggests, would break R36.

## Additional Context
- PR #920 reworded the bullets ("`X`'s job" instead of "use `X`", plus a line saying the skill never invokes them). Whether that is enough for the reviewer is not yet known.
- Possible fix: in dependency-reviewer's Step 3, count only `Skill()`/`Agent()` invocations and documented hand-offs inside a procedure as edges, and state that a When NOT to Use or "use X instead" routing line is not an edge. A dependency-reviewer eval with a reciprocal-exclusion pair would guard it.
- Related: #754 (dependency-reviewer covers only the Skill()/Agent() call graph).
