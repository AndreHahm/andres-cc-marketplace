## Summary

<!-- What does this PR do, and why? 1-3 sentences. -->

## Type of Change

- [ ] feat — new feature
- [ ] fix — bug fix
- [ ] docs — documentation only
- [ ] refactor — code change that neither fixes a bug nor adds a feature
- [ ] perf — performance improvement
- [ ] test — adding or fixing tests
- [ ] chore — build process, tooling, dependencies
- [ ] experiment — experimental change

## Related Issue

<!-- Link the issue this PR addresses, e.g. "Closes #123". Use "N/A" if none. -->

## Changes

<!-- Bullet list of the key changes in this PR. -->

## Testing

<!-- How was this verified? Commands run, tests added, manual steps taken. -->

## Checklist

- [ ] PR title follows conventional commit format (`type(scope): description`)
- [ ] Self-reviewed the diff
- [ ] Tests added/updated where applicable
- [ ] Documentation updated where applicable

## Known CI Failures (Accepted)

<!-- Any CI check expected to fail for a known, already-reviewed reason -- e.g. this PR touches
     review-dispatch-critical (Tier-1) code, so `Codex delta review` will hard-refuse per
     marketplace-ci.yml's trust-boundary gate (see docs/ci.md, issue #351) and needs the
     SHA-bound bypass-attestation protocol (comment + `s: codex review bypassed` label, or
     `--bypass-codex-review "<reason>"` via commit/create-pr/merge-pr). Describe which check(s)
     and why below. -->

- [ ] A specific CI check is expected to fail for a known, accepted reason (described above) — N/A otherwise

## Accepted Review Findings

<!-- Review findings this PR deliberately leaves in place, from any reviewer: CI's Codex delta
     review, CodeRabbit, Devin, the Codex connector, a human reviewer. One line per finding:
       - <rule or reviewer> <path>:<line> @<fingerprint> – accepted|residual|deferred #<issue>|refuted: <reason or link>
     accepted = an accepted risk; residual = a disclosed limitation; deferred = filed as an open
     issue (the #<issue> is required); refuted = shown not to be a defect. For a CI Codex delta
     review finding, copy the line the job summary prints, rule (`-` when it has none), line (`0`
     when it has none) and `@<fingerprint>` (`@-` without a line) included: CI then stops blocking
     on it, also when it is reported again after the file changes, until the flagged line itself
     changes (docs/ci.md, "CI review delta"; R7). A finding on a gate-critical path or from
     security-reviewer also needs a maintainer's comment `- confirmed <rule> <path> @<fingerprint>`.
     Lines that are not applied are listed in the job summary. Every reviewer reads this section
     (R17). A path with spaces cannot be matched. An open issue that tracks a known defect gets a
     line of its own, `- tracked #<issue>: <reason>` (at most 10): reviewers mark a finding that is
     that defect `[tracked #<issue>]`, and CI shows it as tracked instead of blocking (R18); on a
     gate-critical path or from security-reviewer only after a maintainer's comment
     `- confirmed tracked #<issue> <path>`. Use "None" if none. -->

## Open Items (disclosed, not blocking)

<!-- Known limitations, deferred work, or gaps disclosed but not blocking this merge. Use "None" if none. -->
