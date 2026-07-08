# Skill File Merge Extension

Use this extension when merging Markdown files that represent reusable skills, especially `SKILL.md` files with frontmatter, reference tables, allowed tools, examples, constraints, and output contracts.

## Reference Path Drift Rule

When multiple files reference similar support files using different base directories, preserve all references and flag the path drift.

Examples:

- `reference/code-review-checklist.md`
- `references/review-checklist.md`

Do not normalize paths automatically unless the target repository convention is known.

If references appear semantically equivalent but use different paths, keep both in the merged Reference Files section and add a merge note.

## Nested Metadata Union Rule

When frontmatter contains nested metadata objects, merge compatible keys recursively.

For list-like scalar fields such as `triggers` or `related-skills`, create a deduplicated union.

Preserve source-specific metadata such as:

- `author`
- `version`
- `license`
- `context`
- `agent`
- `last-reviewed`

If version values differ, keep the newest or highest semantic version and document the source.

If metadata values conflict semantically rather than structurally, document the conflict in the merge report instead of overwriting it silently.

## Executability Rule for Tool Selection

After merging the body, verify that all referenced tool actions are allowed by frontmatter.

If the merged document contains shell commands, git commands, package-manager commands, security scanners, test runners, or verification commands, ensure `Bash` is present in `allowed-tools`.

If `Bash` is not allowed but required by preserved workflow steps, mark a tool conflict and either:

1. add `Bash`,
2. remove executable verification steps,
3. or document the unresolved conflict.

For security-sensitive skills, prefer least privilege, but do not make the merged workflow non-executable by removing required tools.

## Output Format Composition Rule

When multiple output formats are compatible, compose them instead of choosing one.

Use the richer human-readable structure as the main report and preserve stricter completion lines, verdict formats, evidence requirements, or machine-checkable summaries as mandatory final blocks.

Treat formats as incompatible only when one explicitly forbids the other, such as JSON-only output with no prose.

## Authorization and Safety Constraint Preservation Rule

When merging security, penetration-testing, infrastructure, or active-testing skills, preserve all authorization, scope, rules-of-engagement, and non-disruption constraints.

Do not weaken constraints such as:

- verify written authorization
- stay within defined scope
- do not test production without authorization
- do not exceed proof-of-concept exploitation
- do not cause service disruption or data loss
- report critical findings immediately

If one source contains active testing or offensive-security language and another does not, keep the stricter safety constraints in the merged skill.


## Active Testing Escalation Rule

If a merged security skill includes penetration testing, reconnaissance, exploitation, active validation, proof-of-concept exploit confirmation, live target testing, or other offensive-security activity, add an explicit gate before those steps.

The merged workflow must require confirmation of:

- written authorization
- target scope
- rules of engagement
- approved test environment or approved production testing window
- non-disruption expectations
- proof-of-concept boundaries

If any of these are missing, ambiguous, or contradicted by another source, stop before active testing and ask the human for clarification or approval.

This gate applies even if the original source mentions authorization only once.

When merging, promote scattered authorization notes into one executable workflow step named `Authorization Gate` or equivalent.

## Compliance and Domain Expansion Rule

When one source is a narrow application-security review skill and another expands into compliance, infrastructure, cloud, SAST, dependency auditing, or penetration-testing workflows, classify the relationship carefully:

- If both share the same `name` and runtime purpose, use `same-entity-style-drift`.
- If one file is clearly a specialized overlay, use `base-plus-overlay`.
- If the expanded domain would materially change the skill's intended scope, preserve the expansion but document the broadened scope in merge notes.


## Reference Expansion Rule

When merging reference documents on the same topic, classify them as `same-topic-reference-expansion` if they share the same domain but differ in granularity, lifecycle phase, usage mode, or audience.

Examples:

- review checklist + implementation checklist
- audit checklist + pre-commit checklist
- compliance reference + quick reference
- security checklist + OWASP mapping
- human-readable guidance + machine-gate severity rules
- troubleshooting guide + operational runbook
- architecture reference + coding checklist

For `same-topic-reference-expansion`:

1. Preserve all unique checklist items.
2. Group controls by lifecycle phase first, then by domain or concern.
3. Preserve severity labels where present.
4. Preserve checkbox-style implementation items where present.
5. Preserve code, command, and configuration examples exactly unless they are unsafe.
6. Deduplicate semantically equivalent controls.
7. Keep anti-patterns and common false positives as separate sections.
8. Preserve output, reporting, audit, or gate instructions.
9. Preserve external standards, mappings, and quick-reference tables.
10. Add a merge note when the merged reference broadens the original lifecycle coverage.

Preferred lifecycle grouping for reference expansion:

1. context and threat modeling
2. pre-commit or local checks
3. implementation controls
4. review or audit controls
5. verification and testing
6. reporting and gate criteria
7. anti-patterns and false positives
8. external standards and quick references

Do not force reference documents into a skill, subagent, or slash-command structure unless the source files clearly define runtime behavior.

## Reference Table Consolidation Rule

When multiple files contain reference tables, merge them into one table with columns:

- Topic
- Reference
- Purpose
- Load When

Preserve Markdown links as links.

Preserve inline code paths as exact paths.

Flag any duplicate or near-duplicate reference entries with different paths.

## Security Severity Normalization Rule

When merging security review skills, normalize severity while preserving source semantics.

Default canonical severity scale:

- Critical
- High
- Medium
- Low
- Info

If a source uses CVSS, P0/P1, OWASP risk, or another scale, add a mapping note instead of losing the original meaning.

## Merge Self-Review Additions for Skills

Before finalizing a merged skill, verify:

```text
[ ] Frontmatter is valid and complete.
[ ] Nested metadata was merged recursively.
[ ] Tool permissions match preserved workflow actions.
[ ] All reference files and links are preserved.
[ ] Reference path drift is documented.
[ ] Same-topic reference expansion is classified and organized by lifecycle when applicable.
[ ] Output formats are composed or conflicts are documented.
[ ] Safety and authorization constraints were not weakened.
[ ] Active testing workflows include an explicit authorization gate.
[ ] Severity terminology is normalized.
[ ] The merged skill remains executable and usable as a standalone `SKILL.md`.
```
