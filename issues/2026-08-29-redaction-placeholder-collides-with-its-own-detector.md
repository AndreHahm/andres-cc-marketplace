## Summary
A documented placeholder for redacting a sensitive-data category (a real email address) itself matched that category's own detection regex — following the documented remediation could never pass validation, since the "safe" replacement text is indistinguishable from a real match by the checker's own pattern.

## Environment
- **Product/Service**: `plugin-devkit` plugin — `rule-development`'s security self-check / `rule-reviewer`
- **Region/Version**: this repo, found during PR #164 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Read the documented instruction to redact a real email address by replacing it with `user@example.com`.
2. Run the security self-check / `rule-reviewer`'s email-detection regex (`re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', 'user@example.com')`) against drafted content containing this exact placeholder.
3. The regex matches — the check classifies every match as a failure, so content that correctly followed the redaction instruction is flagged as if it still contained a real email.

## Expected Behavior
A documented placeholder/replacement token for a sensitive-data category should itself be checked against that category's own detection pattern before being documented — a fake-but-real-looking placeholder can trigger the same validator it's supposed to satisfy.

## Actual Behavior
Following the documented remediation could never clear validation, since `user@example.com` is a syntactically valid email address that matches the detection regex exactly like a real one would.

## Impact
[Severity: Medium] A documentation instruction that's structurally impossible to satisfy blocks legitimate work and erodes trust in the validator. Fixed in `plugin-devkit`'s PR #164 (commit `0661014`): live-verified the collision first, then replaced the placeholder with `EMAIL_REDACTED` (matching an existing `API_KEY_REDACTED` convention in the same sentence) and added an explicit note against using a fake-but-real-looking email for exactly this reason.

## Additional Context
Mined from PR #164's own review history (`chatgpt-codex-connector[bot]`; 11 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #164` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/164#discussion_r3880682600
