## Summary
codex-peer-review and codex-verify descriptions route to decision-kit unconditionally, while their bodies say "when installed"; triaging-dependabot-prs names handling-review-findings in a way that reads like a dispatch it holds no grant for.

## Environment
- **Product/Service**: codex-kit `codex-peer-review` and `codex-verify` (`SKILL.md` frontmatter `description`); git-kit `triaging-dependabot-prs` (`SKILL.md` "When NOT to Use")
- **Region/Version**: found in PR #726 at head `17f785738fb9bb40b549b2cdf03db3f323c58f2a`

## Reproduction Steps
1. Read the `description` of `plugins/codex-kit/skills/codex-peer-review/SKILL.md` (around line 14) and `plugins/codex-kit/skills/codex-verify/SKILL.md` (lines 14-16).
2. Compare with the "When NOT to Use" bullets of the same files (codex-peer-review lines 46-48, codex-verify lines 54-58), which PR #726 made conditional on decision-kit being installed and gave a stated fallback.
3. Read `plugins/git-kit/skills/triaging-dependabot-prs/SKILL.md` line 35 against its `allowed-tools` (line 6).

## Expected Behavior
- Each description says the decision-kit route applies when decision-kit is installed, matching its body, or drops the optional-plugin route from the description.
- triaging-dependabot-prs makes clear that running handling-review-findings is the user's step, or holds a matching `Skill(handling-review-findings)` grant if it is meant to dispatch.

## Actual Behavior
- Both descriptions send a critical, security-relevant or uncertain action to `consulting-decision-model` with no installation condition, so the activation text and the body disagree.
- triaging-dependabot-prs line 35 says to ask "whether to triage them first with `handling-review-findings`"; it has no `Skill(handling-review-findings)` grant, and the wording does not say who runs it.

## Error Details
~~~
CI Codex delta review, run 43492881351 (PR #726):
- consistency-reviewer, Major, scope-boundary, plugins/codex-kit/skills/codex-peer-review/SKILL.md:14 (blocking)
- dependency-reviewer, Minor, dependency-graph/tool-scope, plugins/git-kit/skills/triaging-dependabot-prs/SKILL.md:35 (notice)
~~~

## Visual Evidence
N/A

## Impact
Medium: the activation descriptions overstate where a decision check goes when decision-kit is absent, and the triaging-dependabot-prs wording can be read as a dispatch the skill cannot make. No behavior breaks; the bodies already carry the correct routing.

## Additional Context
- Found in PR #726, during round 2 of its review; deferred to this issue at the PR author's direction rather than fixed in that PR.
- Thread/finding: CI run https://github.com/AndreHahm/andres-cc-marketplace/actions/runs/43492881351 (no inline thread; CI Codex delta review findings).
- Reviewer: marketplace CI Codex delta review (consistency-reviewer, dependency-reviewer).
- Severity: Major (codex-peer-review/codex-verify descriptions), Minor (triaging-dependabot-prs wording).
- Suggested fix: add "when decision-kit is installed" to both descriptions (each stays under the 1,024-character limit), and reword triaging-dependabot-prs line 35 so the user runs handling-review-findings; adding the `Skill` grant is a permissions change that needs its own decision.
