## Summary

`issue-opened-labeler.yml`'s `p: critical` keyword regex
(`/\b(critical|urgent|blockers?|blocking|asap|production down)\b/i`) has no negation handling, so
ordinary negated phrasing gets misclassified as critical priority.

## Environment

- **Product/Service**: `.github/workflows/issue-opened-labeler.yml` (live, fires on every issue
  `opened` event)
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps

1. File an issue whose title or body contains a negated phrase matching the regex, e.g. "No blockers
   remain", "this is not urgent", or "non-blocking cleanup".
2. Observe the issue gets auto-labeled `p: critical`.

## Expected Behavior

A negated statement about criticality/urgency should not trigger the `p: critical` label.

## Actual Behavior

`\bblockers?\b`, `\burgent\b`, and `\bblocking\b` all match inside "No blockers", "not urgent", and
"non-blocking" respectively (word-boundary regex doesn't distinguish negated context).

## Error Details

```
N/A -- not a crash. Misclassification: p: critical applied to a non-critical issue.
```

## Visual Evidence

N/A

## Impact

**Severity: Minor.** The mislabel is human-correctable (priority labels are meant to be reviewed), and
`p:` labels are only ever added when missing, never silently re-applied once corrected. Still a real,
verifiable false-positive class worth fixing at the source.

## Additional Context

The identical regex was copied into two new batch workflows in PR #328
(`issue-auto-labeler-batch-run.yml`, `pr-auto-label-batch-run.yml`) for exact parity with this live
file's own classification. That PR added a negation guard (checks ~20 characters immediately
preceding each keyword match for a negation word -- "no", "not", "non", "isn't", "without", etc.) to
its own two copies, but deliberately left this live file unchanged, since editing already-shipped,
event-triggered classification behavior is a separate, more sensitive change than the new-workflow PR
it was found in. This issue tracks porting the same negation guard here, to keep the mirrored
behavior consistent again.

## Review Finding Source

- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/328
- **Head SHA at time of finding**: 74acdb2e1d0a2b4b0dd785c2d3b5bb1259230f22
- **Review thread**: https://github.com/AndreHahm/andres-cc-marketplace/pull/328#discussion_r4010612861
- **Reviewer**: chatgpt-codex-connector (Codex)
- **Stated severity**: P2
