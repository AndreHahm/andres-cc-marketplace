# Report Discovery Convention

Canonical definitions for two facts every report-producing skill and `starting-an-analysis` restate inline: the `<scope-slug>` convention and the report-discovery glob. This file is the source of truth for both — if either changes, sweep every site listed below (R20-style) rather than editing one copy and leaving the rest stale.

**This file, and every other file under `plugins/analysis-kit/references/`, also has a manually-maintained
mirror under `.claude/references/` — copy any edit there too.** `scripts/marketplace_ci`'s
`sync-plugin-mirrors` only auto-mirrors `skills/`, `agents/`, `commands/`, `hooks/`, and `rules/`
(`COMPONENT_DIRS` in `scripts/marketplace_ci/sync.py`) — a plugin-root `references/` directory is
structurally outside its scope and is never auto-synced. This bit twice in the same PR
(`report-evidence-convention.md` shipped with no `.claude/` counterpart at all on the first pass, then
drifted out of sync again on a follow-up edit) before being caught by cross-model review both times —
don't rely on a reviewer to catch a third recurrence; copy the file yourself in the same edit.

## `<scope-slug>`

A short kebab-case description of the scope a report covers, used as the filename prefix: `.claude/output/<skill-name>/<scope-slug>-<timestamp>.md`.

- **Date-range skills** (`analyzing-plugin-components`, `analyzing-tool-and-framework-use`, `analyzing-actor-behavior`, `analyzing-governance-and-conflicts`, `mining-recurring-patterns`): derive from the scope argument — `this-conversation`, `today`, or `<start-date>-to-today` (e.g. `2026-07-10-to-today`).
- **`comparing-sessions`**: derive from the two things being compared, e.g. `<current-scope>-vs-<prior-report-slug>`. `<current-scope>` must never itself contain the literal substring `-vs-` — `starting-an-analysis` Phase 4 parses this compound apart by splitting on the first `-vs-`, so a `<current-scope>` value that already contains it (e.g. inherited from an earlier compound-slugged report) would split wrong; fall back to `this-conversation` in that case.
- **`comparing-session-to-specification`**: derive from the spec document's own filename, e.g. `<spec-basename>-compliance`.
- **`reviewing-analysis-findings`**: for an explicit-list or `"latest N"` run, derive from the reports being cross-checked, e.g. `<skill-a>-and-<skill-b>-<date>`; for a `scope <scope-slug>` run, use the exact input scope-slug unchanged — this is what Phase 1's resolution and Phase 4's supersession check both search for, so persisting under a different, report-comparison-derived slug would make the run's own output unfindable by a later scope run.
- **`generating-analysis-recommendations`**: derive from the source report's own scope-slug, or `pasted-findings-<date>` if findings were pasted directly rather than read from a report.
- **`running-a-full-retrospective`**: reuses whichever `<scope-slug>` its own dispatched date-range analyses used for that run (the shared scope confirmed once in Phase 1) — no independent derivation of its own.
- **`mining-review-learnings`**: not a `<scope-slug>` in this file's sense at all — its own persisted-filename prefix takes one of 3 forms depending on input mode: `<pr-a>-to-<pr-b>` for a since-last-cited run (e.g. `pr-92-to-172`), `merged-<start>-to-<end>` for a merge-date range (e.g. `merged-2026-08-14-to-2026-08-20`), or `pr-<a>-<b>` for an explicit PR list (e.g. `pr-47-51`) — none of them a session/date-range scope identity.
- **`managing-review-learnings`**: derives `<source-slug>` from the input `mining-review-learnings` report's own PR-set slug (e.g. `pr-47-172`), or `direct-finding-<date>` when acting on a user-named finding with no input report at all.

**Two different things share this one name — read this before wiring a new discovery glob.** `<scope-slug>` is used two ways in this plugin: as a *filename prefix* (always — every skill's own Persist step, per the derivations above), and as a *cross-skill discovery filter* (a `<value>-*.md` glob checking "do 2+ reports share this scope," used only at the specific sites listed below — not universally). Whether a site can filter by scope, and by what value, depends entirely on whether that skill's own persisted-filename slug is a value a sibling report could plausibly share:

| Site | Filter used | Why |
|---|---|---|
| 5 date-range skills' own Next-step blocks | `<own-scope-slug>-*.md` | Their own scope-slug *is* the shared session identifier |
| `starting-an-analysis` Phase 5, when a date-range skill or `comparing-sessions` was dispatched | `<captured-value>-*.md` | Mirrors whichever filtered check the dispatched skill's own Next-step block just performed |
| `comparing-sessions`' own Next-step block | `<current-scope>-*.md` (only the shared-identifier half of its own compound slug) | Its full persisted slug (`<current-scope>-vs-<prior-report-slug>`) is unique to one comparison and would never match a sibling report |
| `comparing-session-to-specification`'s own Next-step block | none — any other report besides the one just written | No shared-scope input exists (only a spec path); its own slug (`<spec-basename>-compliance`) is a per-report identifier with no shared counterpart |
| `starting-an-analysis` Phase 5, when `comparing-session-to-specification` was dispatched | none — same "any other report" check | Same reason as above |
| `comparing-sessions` Phase 1 "latest" resolution, `mining-recurring-patterns` Phase 3 memory-recall, `generating-analysis-recommendations` Phase 1, `reviewing-analysis-findings` Arguments block and Phase 1 (`"latest N"` mode) | none — bare, unfiltered glob | These sites list/discover candidate reports generally, not a "does this specific scope already have 2+ reports" check |
| `reviewing-analysis-findings` Phase 1 (`scope <scope-slug>` mode) | `<scope-slug>-*.md` against the 15-directory enumeration **minus `reviewing-analysis-findings` itself** (14 directories), exact-prefix boundary enforced (not a bare substring match) | Resolves the complete compatible *source*-report set for one scope. `reviewing-analysis-findings`'s own persisted-filename slug in scope mode is exactly the input scope-slug (see the `<scope-slug>` table above), so including its own directory here would always self-match a prior aggregation run over this same scope as if it were an independent source report |
| `reviewing-analysis-findings`'s own Phase 4 supersession check | `<scope-slug>-*.md` against `reviewing-analysis-findings/` only, same exact-prefix boundary as Phase 1's resolution | Checks for an earlier findings-review report over the same scope to supersede — deliberately separate from Phase 1's source-report resolution above, which excludes this directory entirely. Applies the same exact-prefix boundary Phase 1 uses (not a bare substring match) — a scope of `team` must not match `team-alpha-<timestamp>.md` here either |
| `running-a-full-retrospective` Phase 1 reuse check | `<scope-slug>-*.md`, filtered per candidate analysis type's own report directory | Checks whether a report already exists for the confirmed scope before dispatching, mirroring each date-range skill's own Next-step filter |
| `mining-review-learnings` Phase 1 "since last cited" resolution | none — bare `Grep` against the live document, not a report glob | Resolves the last-cited PR number from `THIRD_PARTY_REVIEW_LEARNINGS.md` itself, not from a prior report |
| `managing-review-learnings` Phase 1 report resolution | none — bare, unfiltered `Glob('.claude/output/mining-review-learnings/*.md')`, most-recent-modified | Discovers the latest input report generally, not a "does this specific scope already have 2+ reports" check |

`comparing-sessions` and `mining-recurring-patterns` each appear twice above — once with a filter, once without — since each uses both forms in different places within its own file.

## Report-Discovery Glob

analysis-kit's own 15 report directories, named explicitly rather than matched by a prefix wildcard:

```
.claude/output/{analyzing-plugin-components,analyzing-tool-and-framework-use,analyzing-actor-behavior,analyzing-governance-and-conflicts,mining-recurring-patterns,comparing-sessions,comparing-session-to-specification,generating-analysis-recommendations,reviewing-analysis-findings,analyzing-session-outcomes,analyzing-verification-effectiveness,analyzing-session-operations,analyzing-workflow-usability,analyzing-security-and-privacy,identifying-feature-opportunities}/*.md
```

**Interim state, 2026-09-10/11:** `analyzing-session-outcomes`, `analyzing-verification-effectiveness`,
`analyzing-session-operations`, `analyzing-workflow-usability`, `analyzing-security-and-privacy`, and
`identifying-feature-opportunities` were
added here ahead of the Wave 2 plan's own Task 11 (the batch picker/severity/README integration pass)
because
`reviewing-analysis-findings`' own hardcoded discovery globs are load-bearing -- without this
registration, these skills' reports would be silently invisible to the plugin's own cross-check
aggregator. The remaining Task 11 scope (picker taxonomy, severity-vocabulary
mappings, `README.md`/manifest counts, and the other individual date-range skills' own Next-step-block
globs, which are lower cost to leave temporarily stale since they only affect same-skill/same-scope
duplicate-report detection, not discoverability) is still deferred to Task 11 as planned.

**Why explicit, not a prefix wildcard:** a pattern like `.claude/output/{analyzing,comparing,mining,generating,reviewing}-*/*.md` also matches `plugin-devkit`'s unrelated `analyzing-sessions` output directory — confirmed on disk to hold real, unrelated reports. The explicit enumeration above cannot match a foreign plugin's directory no matter what gets added elsewhere in `.claude/output/`.

## Sites That Restate These Facts

Every site below must match this file. If you change either definition here, update all of them in the same pass. Paths are relative to `plugins/analysis-kit/`. **Note on the anti-pattern example above:** the prefix-wildcard pattern shown in "Why explicit, not a prefix wildcard" is a deliberate counter-example kept for documentation — do not count it as a stale site to fix.

- `skills/starting-an-analysis/SKILL.md` — Phase 4 (captures whatever Phase 5 needs from the dispatched skill's printed report path, per the per-site table above) and Phase 5 step 1 (glob, branched by which skill was dispatched). This skill has no `<scope-slug>` derivation step of its own — Phase 4 derives the capture from whatever the dispatched skill actually produced.
- `skills/analyzing-plugin-components/SKILL.md`, `skills/analyzing-tool-and-framework-use/SKILL.md`, `skills/analyzing-actor-behavior/SKILL.md`, `skills/analyzing-governance-and-conflicts/SKILL.md` — each skill's own Persist step (scope-slug) and Next-step block (glob)
- `skills/mining-recurring-patterns/SKILL.md` — Phase 3 memory-recall (glob), Persist step (scope-slug), Next-step block (glob) — three sites
- `skills/comparing-sessions/SKILL.md` — Phase 1 "latest" resolution (glob) and `<current-scope>` derivation (scope-slug), Persist step (scope-slug), Next-step block (glob) — three sites
- `skills/comparing-session-to-specification/SKILL.md` — Persist step (scope-slug), Next-step block (glob)
- `skills/generating-analysis-recommendations/SKILL.md` — Phase 1 (glob), Persist step (scope-slug) — two sites
- `skills/reviewing-analysis-findings/SKILL.md` — Arguments block (glob, 15 directories), Phase 1 `"latest N"` mode (bare glob, 15 directories), Phase 1 `scope <scope-slug>` mode (filtered glob, exact-prefix boundary, **14 directories — excludes `reviewing-analysis-findings` itself**, see the table above), Phase 4 supersession check (filtered glob against its own report directory only), Persist step (scope-slug) — five sites
- `skills/running-a-full-retrospective/SKILL.md` — Phase 1 reuse check (glob, filtered per chosen analysis
  type's own scope-slug), Phase 3 Persist step (scope-slug, reusing whichever date-range scope this run's
  own dispatches used) — two sites. Its own persisted report is deliberately *not* added to the 9-directory
  report-discovery glob enumeration above — see this skill's own Gotchas section for why a meta-report
  consolidating other reports shouldn't count as a 10th independent one
- `skills/mining-review-learnings/SKILL.md` — has no `<scope-slug>` in the sense this file defines it
  (its own persisted-filename prefix takes one of 3 forms — `<pr-a>-to-<pr-b>` for since-last-cited,
  `merged-<start>-to-<end>` for a merge-date range, `pr-<a>-<b>` for an explicit list — none a
  session/date-range scope) and is deliberately *not* added to the 9-directory report-discovery glob
  enumeration above — see this skill's own Gotchas section for its own reason (distinct from
  `running-a-full-retrospective`'s own exclusion reason, which is about consolidation double-counting,
  not scope-shape mismatch)
- `skills/managing-review-learnings/SKILL.md` — Phase 1 report resolution (bare glob, see table above),
  Persist step (`<source-slug>` derivation, see above) — two sites. Like `mining-review-learnings`, its
  own report is deliberately *not* added to the 15-directory glob enumeration, for the same scope-shape
  reason: a `<source-slug>` inherited from a PR-set slug (or `direct-finding-<date>`) has no session/
  date-range identity a sibling report could plausibly share
- `skills/analyzing-session-outcomes/SKILL.md`, `skills/analyzing-verification-effectiveness/SKILL.md`,
  `skills/analyzing-session-operations/SKILL.md`, `skills/analyzing-workflow-usability/SKILL.md`,
  `skills/analyzing-security-and-privacy/SKILL.md`, `skills/identifying-feature-opportunities/SKILL.md`
  — each skill's own Persist step (scope-slug) and
  Next-step block (glob, already written against the 15-directory enumeration including itself, ahead of
  the rest of this sweep -- see the "Interim state" note above)
- `skills/reviewing-analysis-findings/SKILL.md` — swept as part of this same interim registration
  (Arguments block, `"latest N"` mode, and `scope <scope-slug>` mode all now enumerate 15/14 directories
  respectively) since its own discovery is load-bearing, unlike the individual date-range skills' own
  Next-step-block globs, which remain 9-directory pending Task 11
