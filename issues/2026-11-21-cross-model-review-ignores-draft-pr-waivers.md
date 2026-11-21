## Summary
`cross-model-review` reads only the local accepted-findings file, also when the branch already has a draft PR whose body is the authoritative list

## Environment
- **Product/Service**: git-kit `cross-model-review` (Phase 0 step 7 and Phase 3), `plugins/git-kit/scripts/git-review-accepted-findings.py`
- **Region/Version**: PR #822 head `f2db9f98ab6c2bcae455df0560c634dc5cd142c2` (issue #808)

## Reproduction Steps
1. Open a draft PR; copy the local `.claude/accepted-review-findings.local.md` into its `## Accepted Review Findings` section (create-pr step 2).
2. Add a waiver to the draft PR's body, and remove another one from it, without editing the local file.
3. Run `cross-model-review` before flipping the draft to ready.

## Expected Behavior
Once a PR exists, its body's section is the list (R17 in `docs/ci-codex-review-user-requirements.md`). `cross-model-review` reads the PR body's section when the branch has an open PR, and falls back to the local file otherwise, as the local parity review already does (`accepted_findings_source` in `git-codex-parity-review.py`).

## Actual Behavior
`git-review-accepted-findings.py brief` and `match` read only the local file. The review misses the waiver added to the draft and still applies the local copy of the one removed from it.

## Error Details
~~~
None.
~~~

## Visual Evidence
None.

## Impact
Low. `cross-model-review` is a local, advisory pre-ready review; CI applies the PR body. The mismatch can hide or repeat a finding in that local review only. The helper deliberately has no GitHub access, so the fix needs a design choice (pass the body in, as the parity wrapper does through `fetch-accepted-findings`).

## Additional Context
- Found in PR #822.
- PR: https://github.com/AndreHahm/andres-cc-marketplace/pull/822
- Head SHA: `f2db9f98ab6c2bcae455df0560c634dc5cd142c2`
- Thread: https://github.com/AndreHahm/andres-cc-marketplace/pull/822#discussion_r4655038561 (`plugins/git-kit/skills/cross-model-review/SKILL.md:239`)
- Reviewer: Devin
- Severity: Minor
- Related: #808.
