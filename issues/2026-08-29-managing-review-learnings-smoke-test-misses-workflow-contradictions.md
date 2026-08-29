## Summary
`managing-review-learnings`' persisted smoke test only checks structural text presence (e.g. that Phase 2's body names the correct Edit target), so it can't catch a real workflow contradiction between two prose sections that both individually contain the expected text.

## Environment
- **Product/Service**: `analysis-kit` plugin, `managing-review-learnings` skill
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
1. Consider `managing-review-learnings/scripts/smoke_test.py`'s `check_edit_target_named_in_phase_2` check: it greps Phase 2's body text for the literal string `THIRD_PARTY_REVIEW_LEARNINGS.md`.
2. Before this PR's own D4 fix, the Quality Gates checklist (a separate section later in the same file) said Phase 4's issue-draft `Edit` was invalid, while the Gotchas section and Phase 4's own instructions correctly allowed it — a genuine mutually-exclusive contradiction between two sections.
3. The smoke test passed throughout, because it only checks that specific strings are present somewhere in specific sections — it has no way to detect that two present-and-individually-valid statements actually contradict each other.

## Expected Behavior
A test for this skill should be able to catch a scenario where the documented rules for the same action (e.g. "which paths can Phase 4 `Edit`") disagree between two sections, ideally by exercising an end-to-end edited-draft scenario rather than only checking text presence.

## Actual Behavior
The smoke test is structural-only (frontmatter, Bash-grant usage, referenced-file existence, Phase-header sequencing, and this one text-presence check) — it has no mechanism to detect a workflow contradiction between two sections, and the D4 checklist bug shipped and stayed live until an external reviewer caught it by reading the prose.

## Error Details
~~~
N/A -- not a crash. The gap is in test coverage, not runtime behavior.
~~~

## Impact
[Severity: Low] `managing-review-learnings` is a conversational, `AskUserQuestion`-driven skill with no executable logic of its own beyond dispatching `github-issue-lifecycle` and applying `Edit` calls a human already approved — a real end-to-end scenario test would need to simulate that human-approval flow, which is a heavier investment than this skill's existing structural-checks convention (matching every other `analysis-kit`/`plugin-devkit` skill's `scripts/smoke_test.py` shape) currently uses. Declining this as a heavier-than-warranted ask isn't safe either, since the exact contradiction this gap allowed already shipped once (D4) — filing it here to track without blocking this fix batch.

## Additional Context
The specific contradiction this finding cites (D4: the Quality Gates checklist vs. the Gotchas section, both describing Phase 4's `Edit` scope) is already fixed as part of this same PR. This issue tracks the underlying test-coverage gap that let it ship unnoticed, not the contradiction itself.

## Review Finding Source
- **PR URL:** https://github.com/AndreHahm/andres-cc-marketplace/pull/179
- **Head SHA (at time raised):** 5f543b62c7756df1b6592772acb26d90160d6124
- **Review thread/comment:** https://github.com/AndreHahm/andres-cc-marketplace/pull/179#discussion_r3885942265
- **Reviewer:** Devin (devin-ai-integration[bot])
- **Stated severity:** 🔍 (Devin "analysis" kind, unlabeled numeric severity)

Found in PR #179.
