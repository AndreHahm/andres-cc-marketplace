# Governance and Conflict Report — this conversation

**Requested scope:** This conversation — the session transcript describing a fix to a stale skill-count
in `docs/onboarding.md` for the (fixture) `widget-kit` plugin, plus the fixture's own disclosed note about
two other independently-restated, still-stale copies of the same fact.
**Inspected scope:** The full session transcript was read directly. Phase 2's shared rule inventory
(`component_inventory.py`) was run for real against this repository's actual `.claude/rules/*.md` files
(22 rules returned, plus this repo's own real output artifacts — see Unavailable evidence). No
`session_parser.py`/`codex_session_parser.py` call was needed: scope was supplied as `"this conversation"`,
which resolves directly per `date-range-scope-convention.md` without a session-log lookup.
**Unavailable evidence:** The two additional consumer sites the fixture names —
`plugins/widget-kit/README.md`'s opening summary and `plugins/widget-kit/.claude-plugin/plugin.json`'s
`description` field — are explicitly fixture-only per the transcript's own embedded note (`widget-kit`
does not exist in this repository) and were **not** independently verified via `Grep`/`Glob`, per the
fixture's explicit instruction not to search for them on disk. Their existence and staleness are taken as
given fixture fact, not independently confirmed against real files.
**Limitations:** This is a short, single-topic fixture session (two user turns, one assistant action) with
no dispatched agents, no cited spec/plan/architecture document, and no reference to a prior session's
report on this same topic — several of Phase 3's/Phase 4's categories are legitimately empty outcomes here,
not gaps in the check itself.

---

## Rule/Boundary Conformance

### Phase 2 — Rule and Boundary Inventory

`component_inventory.py --project-root .` returned 22 real `.claude/rules/*.md` files from this
repository (list: `ask-before-config-decisions.md`, `ask-before-structural-grounding.md`,
`consult-naming-conventions-first.md`, `disclose-before-overriding-decisions.md`,
`orphaned-worktree-git-read-fallthrough.md`, `plugin-rulebook-enforcement.md`,
`read-and-retrace-skill-chains-before-finalizing.md`, `recheck-state-before-side-effecting-action.md`,
`require-declared-plugin-language.md`, `require-gitignored-scratch-locations.md`,
`require-inventory-updates-for-new-plugins-and-components.md`,
`require-security-review-before-new-gate.md`, `require-tests-for-behavior-changes.md`,
`require-worktree-rooted-absolute-paths.md`, `resolve-activation-overlap-bidirectionally.md`,
`resweep-closed-scope-lists-on-new-components.md`, `route-through-git-kit-lifecycle-skills.md`,
`skill-evaluation-protocol.md`, `starting-work-before-first-change.md`, `test-against-example-plugin.md`,
`verify-rule-scope-before-lazy-loading.md`, `verify-scope-declarations-before-finalizing.md`,
`verify-tool-behavior-before-instructing.md`), plus several real `output_artifact` entries already
present in this repo from unrelated prior runs.

<!-- finding:start -->
**Governance conformance verdict: no applicable violation found.** None of this repository's 22 rules
govern a general obligation to sweep every restatement site of a documented fact when fixing one of them
— the closest candidate, `plugin-rulebook-enforcement.md`'s R20 "Duplicate Fact Sweep Trigger," is scoped
specifically to canonical values inside `plugin-rulebook`'s own `assets/settings.json` and
`inventory_common/models.py` enums, not to a general plugin's own skill-count documentation (and the
fixture's `widget-kit` plugin is not a `plugin-devkit` rulebook target in the first place). This is the
expected, by-design outcome per this skill's own framing: the fixture's actual issue is structural drift
that exists **independent of any rule naming it** — exactly the gap Phase 5 exists to catch instead of
Phase 3/Phase 2.

Evidence origin: direct
Coverage: complete
Confidence: high
Evidence source: `.claude/rules/plugin-rulebook-enforcement.md` (R20 section); `component_inventory.py`
live output
<!-- finding:end -->

### Phase 3 — Conflict Detection

- **Agent-vs-agent:** None found. No agent was dispatched within the scoped transcript — a single
  assistant turn made one direct edit.
- **Rule-vs-rule:** None found. `Grep`ing the 22 rule files above for overlapping keywords relevant to
  this session's action (`stale`, `duplicat`, `mirror`, `consumer`, `blast radius`) surfaced 11 candidate
  rules, all scoped to this repo's own `plugin-devkit`/git-kit governance machinery (R20 sweeps, worktree
  mirrors, skill-chain retracing) — none contradicts another on the fixture's actual situation (fixing a
  stale count in a third-party-style plugin's onboarding doc).
- **Spec-vs-code:** None found. No spec/plan/architecture document was read or cited in the transcript,
  and none of the common spec locations (`docs/`, `specs/`, `ARCHITECTURE.md`, `CONSTITUTION.md`,
  `PROJECT_BRIEF.md`) were referenced by the fixture's own two-turn exchange.
- **Session-vs-session:** None found. The transcript names no prior session's persisted report on this
  same topic (real prior reports found in this repo's own `.claude/output/` tree belong to unrelated
  analyses of a different actual conversation, not this fixture, and are not in evidentiary scope for a
  session-vs-session check here).

<!-- no-findings -->
(Phase 3 produced zero substantive findings — a legitimate, explicitly marked outcome per
`report-evidence-convention.md`, not an unchecked category. All four categories above were explicitly
checked.)

## Recurring Error Tracking (Phase 4)

No command failures, test failures, tool errors, scope conflicts, user corrections, config errors, or
permission denials occurred within the scoped transcript — the user's single request was carried out
without incident, and the user's only follow-up was an acknowledgement ("Great, thanks."). There is
nothing to classify under this phase's taxonomy for this scope; the substantive issue this session
actually left behind (an incomplete fix relative to the fact's full duplication footprint) is a
maintenance-risk finding, not a recurring mistake/error episode, and is reported once, under Phase 5,
rather than double-counted here.

<!-- no-findings -->

## Maintainability & Change Impact (Phase 5)

### Duplication / Documentation Drift / Canonical-Fact Drift / Blast Radius

<!-- finding:start -->
**Finding: the widget-kit skill-count fact is duplicated across 3 sites; only 1 was updated, leaving 2
independently stale.**

- **Canonical source:** No single source of truth is designated for this fact today. The
  actually-authoritative source *should* be a derived count of `plugins/widget-kit/skills/*` itself (now
  7 directories, per the user's own statement that they "just added a 7th (`widget-export`)"), but nothing
  in the fixture's scenario ties any of the three prose restatements below to that directory automatically
  — each is a hand-maintained copy of the same fact.
- **All known consumers (3):**
  1. `docs/onboarding.md` — the site the session actually touched. **Updated this session:** now reads
     "7 skills." Matches the real count.
  2. `plugins/widget-kit/README.md`, opening summary paragraph — **not touched this session.** Per the
     fixture's own disclosed note, still reads "6 skills." **Stale** — drifted from the real count the
     moment the 7th skill was added, and the session's fix did not reach it.
  3. `plugins/widget-kit/.claude-plugin/plugin.json`, `description` field — **not touched this session.**
     Per the fixture's own disclosed note, still reads "6 skills." **Stale** for the same reason as #2 —
     this is arguably the higher-severity of the two remaining stale sites, since a plugin manifest's own
     `description` is the field most likely to be surfaced verbatim to an end user browsing the
     marketplace listing, not just an internal doc.
- **Current state per consumer:** 1 of 3 sites matches the real count (7); 2 of 3 are stale (still say 6).
  This is canonical-fact drift already manifested, not merely a duplication risk — the copies now
  actively disagree with each other, not just with a hypothetical future edit.
- **Blast radius:** 2 remaining sites need the same one-line correction the session already applied to
  the third. The fix is small per-site, but the session's own report of "fixed" is accurate only for the
  one site it touched — a reader trusting "the count is fixed" project-wide would be wrong for the other
  two.

Evidence origin: direct (from the transcript's own explicitly embedded fixture note, which states this as
given fact for the purpose of the exercise, not something independently re-verified against real files)
Coverage: complete (all sites the transcript discloses are enumerated above; per the fixture's own
explicit instruction, no `Grep`/`Glob` was run against real `widget-kit` files, since the plugin does not
exist in this repository)
Confidence: high (the fixture states the staleness directly and unambiguously, leaving no inferential gap)
Evidence source: `session-transcript-blast-radius.md` (fixture note following the transcript's second
turn)
<!-- finding:end -->

### Ownership

<!-- finding:start -->
**Finding: no owner is assigned for keeping the three restatements of this fact in sync.**

Nothing in the fixture's scenario designates who (a person, a convention, or a rule) is responsible for
propagating a skill-count change across `docs/onboarding.md`, the plugin's own `README.md`, and its
`plugin.json` `description` field going forward. The session's own scope (fix the one site the user
pointed at) is a reasonable read of what was *asked*, but the absence of any documented single-owner
convention for this fact is itself the underlying condition that let two sites go stale silently.

Evidence origin: direct
Coverage: complete
Confidence: medium (ownership absence is inferred from the fixture disclosing no such convention, not
from an exhaustive search of a real repo — appropriately weaker than the duplication finding above, which
rests on an explicit disclosed fact rather than an absence)
Evidence source: `session-transcript-blast-radius.md`
<!-- finding:end -->

### Verification Surface

<!-- finding:start -->
**Finding: no check in the fixture's scenario would catch this drift automatically.**

Nothing in the transcript indicates a linter, CI step, or review pass that cross-checks a plugin's stated
skill count across its onboarding doc, README, and manifest description. "No such check exists" is itself
a valid, reportable Verification Surface finding per `change-impact-checklist.md`, rather than something
to leave implicit. (For context, not as evidence about the fixture itself: this real repository's own
`completeness-reviewer` agent is described as checking for exactly this class of drift — "a stated file
count or list that's out of date" — for real plugins it's dispatched against; nothing in the fixture
indicates an equivalent pass was ever run for `widget-kit`, and no rule in this repo's real
`.claude/rules/` obligates one to run automatically on this kind of doc-only edit.)

Evidence origin: direct (fixture) / inferred (the `completeness-reviewer` contextual note, drawn from this
repo's real agent roster, not from anything the fixture itself states)
Coverage: partial (scoped to what the two-turn transcript discloses; whether any check exists for the
*real* `widget-kit`-equivalent plugins in this repo was not surveyed as part of this analysis)
Confidence: medium
Evidence source: `session-transcript-blast-radius.md`; agent roster description for `completeness-reviewer`
<!-- finding:end -->

## Top Actions

1. **Fix the 2 remaining stale sites now, in the same pass as the original fix.** Update
   `plugins/widget-kit/README.md`'s opening summary and `plugins/widget-kit/.claude-plugin/plugin.json`'s
   `description` field to "7 skills," matching `docs/onboarding.md`. (Maintainability — Duplication /
   Canonical-Fact Drift / Blast Radius)
2. **Designate a canonical source for this fact**, or add a lightweight check that cross-references the
   three sites, so the next skill addition doesn't require remembering all three by hand. (Maintainability
   — Ownership / Verification Surface)
3. No Phase 3/Phase 4 action items — both categories returned clean for this scope.
