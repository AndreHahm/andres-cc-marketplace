# tracking-recommendation-lifecycle: redaction covers secret-shaped patterns but not names or emails in free text

## Summary

The skill appends user-pasted rationale and evidence to events.jsonl under .claude/output/analysis-kit-recommendations/. Its note says secret-shaped patterns are redacted.

## Environment

- Repository: AndreHahm/andres-cc-marketplace, branch `fix/propagate-allowed-tools-correction`
- File: `plugins/analysis-kit/skills/tracking-recommendation-lifecycle/SKILL.md` line 92

## Reproduction Steps

Read the file at the cited line on the reviewed head commit.

## Expected Behavior

Redact or warn about personal data in free text, or word the note to say only secret-shaped patterns are handled.

## Actual Behavior

Names, emails and other personal data in free-text fields are not redacted, although the note can be read as covering all sensitive data.

## Error Details

Not applicable: this is a documentation or design finding, not a runtime error.

## Visual Evidence

Not applicable.

## Impact

Personal data pasted into rationale or evidence is persisted in a local output file.

## Additional Context

- Found in PR #675 (https://github.com/AndreHahm/andres-cc-marketplace/pull/675)
- Reviewed head SHA: 862fa4b4 (CI round 10; the export item: 454aac18, round 9)
- Reviewer: security-reviewer (Codex delta review), severity: Minor
- Deferred as out of the PR's scope; the text pre-dates the PR or sits next to lines it changed.
