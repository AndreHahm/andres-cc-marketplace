# Standard Sections (R35)

Full detail for R35. `SKILL.md` carries the rule's statement and a pointer here. Forward-looking, like
R28-R30: checked on newly-created or structurally-modified skills, not as a sweep of every existing one.

## Required headings

A skill's `SKILL.md` must contain these four `##` sections (headings match case-insensitively, so `## When Not to Use` counts):

| Section | Required when |
|---|---|
| `## Quick Start` | Always |
| `## When to Use` | Always |
| `## When NOT to Use` | Always |
| `## Reference Guide` | The skill has a `references/` directory |

Headings are matched by substance, not exact wording, the way R29 matches its subsections: a heading such
as `## When to Use This Skill` satisfies `## When to Use`. The accepted heading patterns are configured in
`assets/settings.json → rules.R35_standard_sections_required.config.required_sections`.

## Not checked here: Testing & Validation

`## Testing & Validation` is deliberately not part of this rule. R29 already fails a `SKILL.md` with no such
heading, so listing it here would report one missing heading twice.

## Why four sections

`plugin-rulebook-checker` reads only the compact checklist, so a convention that lives only in
`skill-development/references/checklist.md` (read by `skill-reviewer`) is invisible to it. The overlap with that checklist is intended: R35 is the
rule the checker can see.

## Fix

Add the missing section. A skill with no `references/` directory does not need `## Reference Guide`.
