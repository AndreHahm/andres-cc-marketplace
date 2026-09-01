## Summary
`plugin-grader`'s plugin-mode report shape (`references/output-schema.md`'s `components` object, and Step 4's `component_scores` rollup input) is keyed by bare component name only — two active components sharing a name but differing by type (e.g. a skill and a command both named `docs`, which `plugin-inventory` itself explicitly allows via its own `(name, type)` uniqueness key) silently collide, and one grade is dropped before the report is ever written.

## Environment
- **Product/Service**: plugin-devkit's `plugin-grader` skill (this marketplace repo)
- **Region/Version**: `plugins/plugin-devkit/skills/plugin-grader/` and its `.claude/skills/plugin-grader/` mirror
- **Browser/OS**: N/A

## Reproduction Steps
1. Create a plugin with two active components sharing the exact same `name` but different `type` — e.g. a skill `docs` and a command `docs`.
2. Grade the plugin in plugin mode (`plugin-grader <plugin-name>`).
3. Inspect the written report's `components` object (or the `component_scores` rollup input built during Step 4).

## Expected Behavior
Both components' grades should be present and importable — `plugin-inventory` itself allows two active records with the same name when their types differ, so the grading report's own shape should be able to represent both.

## Actual Behavior
`components`/`component_scores` are plain `{"<name>": {...}}` dicts. When two components share a name, the second one built silently overwrites the first during report construction — only one of the two grades ever reaches the written report. Nothing downstream (including plugin-grader's own Step 8, "Offer Inventory Import") can detect or recover the dropped grade, since it only ever sees whatever the report actually contains.

## Error Details
~~~
No error is raised anywhere in this path — the collision is silent. The only observable symptom is that one of the two same-named components' scores never appears in scoring_history after an otherwise-successful plugin-mode grade + import.
~~~

## Visual Evidence
N/A

## Impact
Medium — real, silent data loss (a computed grade is dropped, never surfaced as missing), but requires two active components in the same plugin sharing an exact name with different types, which is a real but uncommon configuration in this marketplace's own current plugin set.

## Additional Context
The fix needs composite `(name, type)` keys across `references/output-schema.md`'s Plugin Mode section, Step 4's rollup-input construction, `assets/example-output-plugin.json`, and every consumer of this shape — genuinely bigger than the PR that surfaced it (#271, which only added a new consumer of the pre-existing shape, Step 8's inventory-import offer). Scoped out of that PR per its own review-triage decision; Step 8's own text carries a "Known limitation, not fixed here" disclosure pointing back to this issue in the interim.

## Review Finding Source
- **PR URL**: https://github.com/AndreHahm/andres-cc-marketplace/pull/271
- **Head SHA the finding was raised against**: `8dc34e95829e68386252b6cf0ca968faf3b4b8f3`
- **Review thread/comment**: https://github.com/AndreHahm/andres-cc-marketplace/pull/271#discussion_r3900877328 (comment id `3900877328`)
- **Reviewer**: Devin (`devin-ai-integration[bot]`)
- **Stated severity**: 🟡 (Devin's own "bug" classification, no explicit P-level)
