## Summary
`session_parser.py` returns no message text for Claude session transcripts, so `mining-review-learnings`' Phase 2 cross-check can't actually match a session to a PR by content or compare the session's own account against a review finding's stated root cause.

## Environment
- **Product/Service**: `analysis-kit` plugin, `mining-review-learnings` skill
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
1. Run `mining-review-learnings` against any merged PR whose fix was authored in a Claude Code session.
2. Phase 2 calls `session_parser.py` to search for a transcript covering that PR.
3. Inspect the script's own output shape: it exposes `role`, `timestamp`, tool names, `usage`, and `text_length` per event — no message text and no tool inputs/results.
4. Observe that nothing in the returned data lets the skill confirm a transcript actually discusses the PR in question (by PR number, branch name, or finding content), or compare the transcript's own account of a root cause against what the review comment says.

## Expected Behavior
`mining-review-learnings`' Phase 2 "Cross-check" field should be able to state whether a session transcript's own account agrees or diverges from a review comment's stated root cause, based on actual message content.

## Actual Behavior
The skill can only report a transcript's *existence* and coarse shape (turn counts, tool-call counts, token usage) — never its content — so the "Cross-check" field can never be more than "available, but content is inaccessible; agreement/divergence could not be assessed."

## Error Details
~~~
N/A -- not a crash. `session_parser.py`'s documented output fields (role, timestamp,
tool names, usage, text_length) simply omit message text and tool inputs/results by design.
~~~

## Impact
[Severity: Medium] `mining-review-learnings`' own advertised "Cross-check" capability (comparing a session transcript's account against a review finding) is currently unusable for its stated purpose whenever a session transcript is found — every real cross-check in practice degrades to "unavailable" or "content inaccessible," even though the transcript exists and `session-transcript: available` is reported. This doesn't block the skill's core mining function (finding and cataloging review findings), only the transcript cross-check enrichment.

## Additional Context
`session_parser.py` is a *shared* script used by 5+ sibling `analysis-kit` skills — any fix here needs to weigh real privacy/PII implications of exposing raw message text as a new output field, which is why this was deliberately not decided unilaterally inside a review-findings-fix pass and is being filed as a design decision instead. A fix should likely add a purpose-built, narrowly-scoped extraction path (e.g. matching by PR number/branch name/finding keyword, returning only the matching excerpt) rather than a blanket raw-message-text dump, to keep the privacy exposure bounded.

## Review Finding Source
- **PR URL:** https://github.com/AndreHahm/andres-cc-marketplace/pull/179
- **Head SHA (at time raised):** 5f543b62c7756df1b6592772acb26d90160d6124
- **Review thread/comment:** https://github.com/AndreHahm/andres-cc-marketplace/pull/179#discussion_r3885942084
- **Reviewer:** Devin (devin-ai-integration[bot])
- **Stated severity:** 🟡 (Devin "bug" kind, unlabeled numeric severity)

Found in PR #179.
