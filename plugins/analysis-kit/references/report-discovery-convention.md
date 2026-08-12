# Report Discovery Convention

Canonical definitions for two facts every report-producing skill and `starting-an-analysis` restate inline: the `<scope-slug>` convention and the report-discovery glob. This file is the source of truth for both — if either changes, sweep every site listed below (R20-style) rather than editing one copy and leaving the rest stale.

## `<scope-slug>`

A short kebab-case description of the scope a report covers, used as the filename prefix: `.claude/output/<skill-name>/<scope-slug>-<timestamp>.md`.

- **Date-range skills** (`analyzing-plugin-components`, `analyzing-tool-and-framework-use`, `analyzing-actor-behavior`, `analyzing-governance-and-conflicts`, `mining-recurring-patterns`): derive from the scope argument — `this-conversation`, `today`, or `<start-date>-to-today` (e.g. `2026-07-10-to-today`).
- **`comparing-sessions`**: derive from the two things being compared, e.g. `<current-scope>-vs-<prior-report-slug>`.
- **`comparing-session-to-specification`**: derive from the spec document's own filename, e.g. `<spec-basename>-compliance`.
- **`reviewing-analysis-findings`**: derive from the reports being cross-checked, e.g. `<skill-a>-and-<skill-b>-<date>`.
- **`generating-analysis-recommendations`**: derive from the source report's own scope-slug, or `pasted-findings-<date>` if findings were pasted directly rather than read from a report.

## Report-Discovery Glob

analysis-kit's own 9 report directories, named explicitly rather than matched by a prefix wildcard:

```
.claude/output/{analyzing-plugin-components,analyzing-tool-and-framework-use,analyzing-actor-behavior,analyzing-governance-and-conflicts,mining-recurring-patterns,comparing-sessions,comparing-session-to-specification,generating-analysis-recommendations,reviewing-analysis-findings}/*.md
```

**Why explicit, not a prefix wildcard:** a pattern like `.claude/output/{analyzing,comparing,mining,generating,reviewing}-*/*.md` also matches `plugin-devkit`'s unrelated `analyzing-sessions` output directory — confirmed on disk to hold real, unrelated reports. The explicit enumeration above cannot match a foreign plugin's directory no matter what gets added elsewhere in `.claude/output/`.

## Sites That Restate These Facts

Every site below must match this file. If you change either definition here, update all of them in the same pass. Paths are relative to `plugins/analysis-kit/`. **Note on the anti-pattern example above:** the prefix-wildcard pattern shown in "Why explicit, not a prefix wildcard" is a deliberate counter-example kept for documentation — do not count it as a stale site to fix.

- `skills/starting-an-analysis/SKILL.md` — Phase 4 (captures the dispatched skill's actual scope-slug from its printed report path) and Phase 5 step 1 (glob). (This skill's own body has no `<scope-slug>` derivation step of its own — Phase 4 reads whatever scope-slug the dispatched skill actually produced, and Phase 5's glob uses that captured value.)
- `skills/analyzing-plugin-components/SKILL.md`, `skills/analyzing-tool-and-framework-use/SKILL.md`, `skills/analyzing-actor-behavior/SKILL.md`, `skills/analyzing-governance-and-conflicts/SKILL.md` — each skill's own Persist step (scope-slug) and Next-step block (glob)
- `skills/mining-recurring-patterns/SKILL.md` — Phase 3 memory-recall (glob), Persist step (scope-slug), Next-step block (glob) — three sites
- `skills/comparing-sessions/SKILL.md` — Phase 1 "latest" resolution (glob), Persist step (scope-slug), Next-step block (glob) — three sites
- `skills/comparing-session-to-specification/SKILL.md` — Persist step (scope-slug), Next-step block (glob)
- `skills/generating-analysis-recommendations/SKILL.md` — Phase 1 (glob), Persist step (scope-slug) — two sites
- `skills/reviewing-analysis-findings/SKILL.md` — Arguments block (glob), Phase 1 (glob), Persist step (scope-slug) — three sites
