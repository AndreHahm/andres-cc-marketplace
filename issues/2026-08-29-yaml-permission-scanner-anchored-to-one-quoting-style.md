## Summary
A check written against a YAML list entry's literal text must split and normalize each entry (strip surrounding quotes/whitespace) before comparing — anchoring the pattern to one specific quoting style misses YAML's other equally-valid forms for the same value.

## Environment
- **Product/Service**: `codex-kit` plugin (source instance: a smoke test rejecting a prohibited `Skill` grant in `allowed-tools`)
- **Region/Version**: this repo, found during PR #112 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Write a regex-based check that scans an `allowed-tools` YAML flow-sequence list for a prohibited entry, matching only the quoted forms (e.g. `"Skill"`/`'Skill'`).
2. Change the same list to use the bare/unquoted form of the same entry: `allowed-tools: [Read, Grep, Glob, Skill]`.
3. Run the check — it passes, since the regex never accounted for an unquoted flow-sequence scalar.

## Expected Behavior
A check against a YAML list entry's value should split the list and normalize each entry (strip quotes/whitespace) before comparing against the prohibited value — never anchor to one specific quoting style.

## Actual Behavior
A regex matching only `"Skill"`/`'Skill'` missed the equally-legal bare/unquoted `Skill` entry, letting a prohibited grant back into `allowed-tools` undetected.

## Assumed vs. actual

| Assumed | Actual |
|---|---|
| A grant name in a YAML flow sequence is reliably quoted | YAML flow-sequence scalars are valid either quoted or bare — a check anchored to one form misses the other |

## Impact
[Severity: Medium] A security-relevant tool-grant check (blocking a prohibited `Skill` grant) had a real bypass. The specific instance was already fixed in `codex-kit`'s PR #112 (commit `53b04cac0a`), which splits/normalizes entries and adds a controlled negative for the bare form. This issue is about the *general* convention: no `.claude/rules/*.md` file currently states "a YAML-list-entry check must normalize quoting before comparing" — this repo has multiple `allowed-tools`/frontmatter validators across `plugin-rulebook`, `analysis-kit`, `codex-kit`, and others that could carry the same quoting-blind gap.

## Additional Context
Mined from PR #112's own review history (`coderabbitai[bot]`; 28 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #112` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue. This extends the existing repo-wide theme already documented in `.claude/rules/verify-tool-behavior-before-instructing.md` (verify a format/tool's real behavior before writing a check against it) with a new concrete instance: YAML's own multiple valid quoting styles.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/112#discussion_r3843129378

Suggested scope: worth sweeping other `allowed-tools`/frontmatter grant validators in this repo for the same quoting-anchored regex shape.
