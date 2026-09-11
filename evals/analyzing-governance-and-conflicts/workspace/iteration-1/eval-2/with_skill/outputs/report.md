# Governance and Conflict Report

**Requested scope:** This conversation — the synthetic fixture session in which the user asked for a
review of a new `analyzing-widgets` skill before committing it, and `skill-reviewer` and
`consistency-reviewer` were dispatched in sequence against the same file.
**Inspected scope:** The entire session transcript (a single user turn plus two agent dispatch records)
was read in full — nothing in this scope was sampled. `component_inventory.py` was run for real against
this repository's actual `.claude/rules/*.md` tree (22 rules found) and `.claude/output/` artifacts (7
prior artifacts found). The real plugin-rulebook threshold this session's conflict turns on (R21 skill
description size, 1024-char hard max) was independently verified against
`plugins/plugin-devkit/skills/plugin-rulebook/assets/settings.json` and
`plugins/plugin-devkit/skills/plugin-rulebook/references/size-rules.md`, not taken on either agent's
word. The real `skill-reviewer` and `consistency-reviewer` agent definitions
(`plugins/plugin-devkit/agents/*.md`) were also read directly to check whether either agent's own
current instructions actually wire in an R21 check, since that bears on Phase 5's root-cause analysis
below.
**Unavailable evidence:** The `analyzing-widgets` skill itself does not exist anywhere in this repository
(confirmed via `Glob`) — it is fictional for this fixture, so its actual frontmatter could not be
independently re-read; both agents' 1180-character figure is taken as given. No resolution turn exists in
the transcript (it ends immediately after the second agent's findings), so whether/how the contradiction
was eventually reconciled is unknowable from this scope.
**Limitations:** This is a single-turn, two-agent-dispatch transcript — far narrower than this skill's
usual "date range of sessions" scope. Phase 4's recurring-error tracking in particular has only one
turn of evidence to draw on, so "recurring" claims below are explicitly scoped to what a single episode
can support, not a confirmed multi-episode pattern. Three prior `.claude/output/` reports exist for a
`this-conversation` scope-slug in this repository, but all three (`analyzing-actor-behavior`,
`analyzing-governance-and-conflicts`, `running-a-full-retrospective`, all dated 2026-09-11) are about a
different, unrelated real session (a Wave 2 capability-expansion build for `analysis-kit`) — see Phase 3's
Session-vs-session finding below for why none of them qualifies as "in scope" for this fixture.

## Phase 2: Rule and Boundary Conformance

`component_inventory.py --project-root .` found 22 rules under `.claude/rules/` (plus 7 pre-existing
`.claude/output/` artifacts, listed and dispositioned in the preamble above). Checked each against this
session's own narrow scope per `governance-conformance-checklist.md`.

### Checked, no clearly applicable triggering situation found in this session

Given the transcript's actual content (one user request, two agent dispatches, no commits, no branch/
worktree activity, no config decisions, no new plugin component), the great majority of the 22 rules have
no applicable triggering situation here: `ask-before-config-decisions.md`, `ask-before-structural-
grounding.md`, `consult-naming-conventions-first.md`, `orphaned-worktree-git-read-fallthrough.md`,
`read-and-retrace-skill-chains-before-finalizing.md`, `recheck-state-before-side-effecting-action.md`,
`require-declared-plugin-language.md`, `require-gitignored-scratch-locations.md`,
`require-inventory-updates-for-new-plugins-and-components.md`, `require-security-review-before-new-
gate.md`, `require-tests-for-behavior-changes.md`, `require-worktree-rooted-absolute-paths.md`,
`resweep-closed-scope-lists-on-new-components.md`, `route-through-git-kit-lifecycle-skills.md`,
`starting-work-before-first-change.md`, `test-against-example-plugin.md`, `verify-rule-scope-before-lazy-
loading.md`, `verify-scope-declarations-before-finalizing.md`.

### Applicable, and violated within this session's own scope

<!-- finding:start -->
**`disclose-before-overriding-decisions.md`** applies here on its "silently skip a workflow phase" /
"silently remove or change existing functionality" clauses, one layer up from the agent-vs-agent
contradiction itself: the transcript shows the assistant receiving a Critical, actionable finding from
`consistency-reviewer` that directly contradicts the "no action needed" verdict `skill-reviewer` gave two
turns earlier on the identical field — and the transcript simply ends there, with no acknowledgement that
the two verdicts disagree, no re-ask, no stated resolution. This rule's own scope note says disclosure
(not necessarily an `AskUserQuestion` re-ask, since no checkpoint decision was made yet) is required
"even when the change is small [or] obviously correct" — silently sitting on a known, direct contradiction
between two dispatched reviewers is the same failure shape one level removed: nothing in the assistant's
own turn tells the user two agents disagree about whether to ship as-is.

Evidence origin: direct
Coverage: complete
Confidence: medium
Evidence source: `session-transcript-agent-conflict.md` (the assistant's final bracketed narration
confirms the contradiction was left unreconciled at transcript end)
<!-- finding:end -->

<!-- finding:start -->
**`verify-tool-behavior-before-instructing.md`** applies by generalization, not by literal tool/API
match: its core discipline — don't state a threshold/behavior claim from memory or an "intuitive"
impression when the real, current source is one read away — is exactly what `skill-reviewer` failed to
do. Verified directly against this repo's own canonical source
(`plugin-rulebook/assets/settings.json`'s `R21_skill_description_size` config and
`references/size-rules.md`'s severity table): the real hard max is 1024 characters, and >1024 is
`❌ Critical`, not a "long but acceptable" warning-free pass. `skill-reviewer`'s 1180-character verdict is
156 characters over that real limit and squarely in the `> 1024` Critical row — this is not a borderline
or debatable call. See Phase 3's agent-vs-agent finding and Phase 5's root-cause finding below for the
mechanism (skill-reviewer's own current gatekeeper checks never load or apply the R21 threshold at all).

Evidence origin: direct
Coverage: complete
Confidence: high
Evidence source: `plugins/plugin-devkit/skills/plugin-rulebook/assets/settings.json` (`R21_skill_
description_size.config.limits.description.max_length: 1024`); `plugins/plugin-devkit/skills/plugin-
rulebook/references/size-rules.md` (`> 1024` row: `❌ Critical — Exceeds the hard max`)
<!-- finding:end -->

### Correctly applied

<!-- finding:start -->
**`plugin-rulebook-enforcement.md`** was correctly exercised by the dispatching assistant's own workflow
shape: a skill under active authorship was checked against `plugin-rulebook` structural limits via a
dedicated reviewer dispatch before commit, matching this rule's "before finalizing... run
`plugin-rulebook`" compliance procedure in spirit (via `consistency-reviewer`, which explicitly names
"plugin-rulebook's structural limits" in its own task prompt) even though the transcript never invokes
`plugin-rulebook`/`plugin-rulebook-checker` by name.

Evidence origin: direct
Coverage: complete
Confidence: medium
Evidence source: `session-transcript-agent-conflict.md` (`consistency-reviewer` dispatch task: "Check
...frontmatter for consistency with plugin-rulebook's structural limits")
<!-- finding:end -->

## Phase 3: Conflict Detection

**Agent-vs-agent — found, the primary finding of this report.**

<!-- finding:start -->
`skill-reviewer` and `consistency-reviewer` were both dispatched against the identical subject — the
`description` frontmatter field of `skills/analyzing-widgets/SKILL.md`, both citing the same 1180-character
figure — and reached directly opposite verdicts:

| | skill-reviewer | consistency-reviewer |
|---|---|---|
| Verdict | PASS, "long but acceptable... well within normal range... no action needed" | Critical, "exceeds plugin-rulebook's documented 1024-character hard limit... should be trimmed before commit" |
| Ground truth (independently verified this run against `plugin-rulebook/assets/settings.json` + `size-rules.md`) | — | Correct: 1180 > 1024 is squarely the `❌ Critical` row |

This is not a matter of the two agents legitimately weighing the same evidence differently — one verdict
is objectively wrong against the project's own live, currently-enabled R21 threshold, not just a
difference of judgment. Per `conflict-taxonomy.md`'s Severity Guidance, this is more severe than a
same-session-caught-and-corrected conflict: the transcript ends with the contradiction still unresolved,
meaning it was one commit action away from either (a) shipping with a real Critical violation if the
assistant had trusted `skill-reviewer`'s "no action needed" verdict, or (b) an unnecessary trim if
`skill-reviewer`'s number had instead been the accurate one and `consistency-reviewer` was wrong — the
transcript gives no signal which risk the assistant was about to run.

Evidence origin: direct
Coverage: complete
Confidence: high
Evidence source: `session-transcript-agent-conflict.md` (both agent-dispatch blocks); cross-checked
against `plugins/plugin-devkit/skills/plugin-rulebook/assets/settings.json` and `references/size-
rules.md` for ground truth
<!-- finding:end -->

**Rule-vs-rule — none found.** Grepped this repository's 22 `.claude/rules/*.md` files for the trigger
keywords this session's own subject matter would touch (`description`, `character`, `frontmatter`,
`1024`, `hard limit`). Seven rules matched on generic overlap (`verify-tool-behavior-before-
instructing.md`, `verify-rule-scope-before-lazy-loading.md`, `test-against-example-plugin.md`,
`resolve-activation-overlap-bidirectionally.md`, `read-and-retrace-skill-chains-before-finalizing.md`,
`plugin-rulebook-enforcement.md`, `consult-naming-conventions-first.md`), but none of the pairs actually
instructs a contradictory action for this session's specific situation (a description-length verdict) —
`plugin-rulebook-enforcement.md` is the only one that substantively governs this subject, and it names
itself as the authority (rulebook wins for plugin-component decisions) rather than conflicting with a
sibling rule. No actual rule-vs-rule contradiction found.

**Spec-vs-code — not applicable, no evidence.** The transcript never reads a spec/plan/architecture
document, and this session's subject (a frontmatter character-count threshold) is governed by
`plugin-rulebook`'s own config, not a spec/plan/architecture doc. Checked this repository's common spec
locations (`docs/`, `ARCHITECTURE.md`, `CONSTITUTION.md`, `PROJECT_BRIEF.md`) per this phase's own
Glob-fallback instruction — `docs/` exists but contains CI/label/mkdocs documentation, nothing bearing on
`analyzing-widgets` or R21 description limits. Nothing to compare.

**Session-vs-session — checked, not applicable.**

<!-- finding:start -->
`component_inventory.py`'s own scan found three prior `.claude/output/` reports carrying a
`this-conversation` scope-slug in this repository (`analyzing-actor-behavior`,
`analyzing-governance-and-conflicts`, `running-a-full-retrospective`, all dated 2026-09-11T14:4x–15:0xZ).
All three were read far enough to confirm their actual subject: a real, different session — the Wave 2
capability-expansion build for `analysis-kit` itself (R13 line-count violations, R29 testing-mandate
gaps, `plugin-inventory` staleness, mirror-sync drift). None of them addresses the `analyzing-widgets`
skill, the `skill-reviewer`/`consistency-reviewer` pair, or R21 description-length at all — they are
about an unrelated topic and an unrelated (real, not fixture) session. Per this phase's own definition,
a prior report only counts as "in scope for comparison" when it's a report on the same session/topic
being extended or revisited; a same-scope-slug coincidence alone does not make a genuinely unrelated
report "in scope." Treated as not applicable rather than silently omitted, per this skill's own
Absence-of-evidence-≠-absence-of-use discipline.

Evidence origin: direct
Coverage: complete
Confidence: high
Evidence source: `component_inventory.py` output (`output_artifact` category, 3 `this-conversation-*`
entries under `analyzing-actor-behavior/`, `analyzing-governance-and-conflicts/`, and
`running-a-full-retrospective/`); each report's own Requested-scope line confirms the unrelated subject
<!-- finding:end -->

## Phase 4: Recurring Error Tracking

With only a single turn of evidence in scope, "recurring" below means "occurred once in the available
window," not a confirmed multi-episode pattern — flagged explicitly per this phase's own instruction to
distinguish a genuine repeat from a superficially similar single instance.

| Item | Category | Status |
|---|---|---|
| `skill-reviewer` produced a factually incorrect quality verdict on the description field's character count — not a borderline judgment call, but a claim ("well within normal range") that contradicts the project's own live, currently-enabled R21 threshold by 156 characters | `other` — ungrounded/incorrect agent verdict | `unresolved` (transcript ends before any correction or re-check) |
| The dispatching assistant received two directly contradictory reviewer verdicts on the same field of the same file and did not flag, reconcile, or re-ask about the contradiction before the transcript ends | `other` — unacknowledged cross-agent contradiction (see Phase 2's `disclose-before-overriding-decisions.md` finding for the applicable-rule angle on this same fact) | `unresolved` |

These are tracked as two distinct items (not merged) because they have different root causes: the first
is a grounding gap inside one agent's own procedure (see Phase 5 below), the second is an orchestration
gap in how the calling assistant handled the two agents' outputs — same category label, different cause,
per this phase's own over-merging guidance.

## Phase 5: Maintainability and Change-Impact Analysis

<!-- finding:start -->
**Verification surface / canonical-fact drift — `skill-reviewer`'s own current procedure never loads or
applies the R21 description-length threshold at all.** Read the real, current `skill-reviewer` agent
definition (`plugins/plugin-devkit/agents/skill-reviewer.md`) directly to find the root cause of the
Phase 3 conflict, rather than treating it as an unexplained one-off mismatch:

- Step 1 (lines 34-38) explicitly scopes its `plugin-rulebook/assets/settings.json` load to **"R13 and
  R18 threshold config"** only — R21 (description size) is not named.
- Step 4's gatekeepers are C1 (SKILL.md line count, backed by R13), C2 (code-block size, backed by R18),
  C3 (frontmatter YAML validity + presence of `name`/`description` — a presence check, not a length
  check), and C4 (description voice/mood — third-person, not length).
- No gatekeeter or step in the file reads or applies `R21_skill_description_size`'s tiered thresholds
  (min 80 / max 1024) to the description field's actual character count anywhere in the current file.

**Canonical source:** `plugin-rulebook/assets/settings.json`'s `R21_skill_description_size` config (the
same source `consistency-reviewer`'s fixture dispatch correctly surfaced, per its task prompt explicitly
asking for "consistency with plugin-rulebook's structural limits"). **Known consumers:** `skill-
reviewer.md` (does not check it — the gap), `consistency-reviewer.md` (does not name R21 by ID either,
but produced the correct number in this transcript because its dispatch prompt specifically pointed it at
plugin-rulebook's structural limits — this session's evidence doesn't establish whether an
untargeted `consistency-reviewer` dispatch would reliably surface R21 on its own). **Current state:**
`skill-reviewer` drifted/never-wired; `consistency-reviewer`'s coverage of R21 is unconfirmed beyond this
one targeted dispatch.

**Verification surface:** nothing in `skill-reviewer.md`'s own file would catch this gap mechanically —
there is no smoke test or structural check asserting that every `TIERED`-severity rule in
`plugin-rulebook/assets/settings.json` (R21 included) has a corresponding gatekeeper step in
`skill-reviewer.md`'s Step 4. This is the direct structural explanation for why the Phase 3 agent-vs-agent
conflict was possible at all, not just a coincidence of one agent happening to guess wrong.

**Ownership:** unclear from the files read — `skill-reviewer.md`'s own header line ("its rules take
precedence over the `skill-development` defaults for size checks (C1/R13 and C2/R18)") already names
exactly two rules (R13, R18) as in-scope for size checks, silently excluding R21 by omission rather than
an explicit decision documented anywhere in the file.

Evidence origin: direct
Coverage: complete
Confidence: high
Evidence source: `plugins/plugin-devkit/agents/skill-reviewer.md` (lines 18, 30-38, 64-96);
`plugins/plugin-devkit/agents/consistency-reviewer.md` (lines 45-51, no R21 reference found);
`plugins/plugin-devkit/skills/plugin-rulebook/assets/settings.json`
<!-- finding:end -->

<!-- finding:start -->
**Coupling — `skill-reviewer` and `consistency-reviewer` cover overlapping ground (both can be asked
about a skill's frontmatter) with no documented division of which rulebook checks each one owns.**
Distinct from the finding above (which is about R21 specifically being missing from one agent): more
generally, nothing in either agent's own file states which of `plugin-rulebook`'s R-numbered checks it is
and isn't responsible for surfacing when dispatched generically (as `skill-reviewer` was in this
transcript's first dispatch, with no explicit "and check plugin-rulebook limits" instruction). A caller
dispatching `skill-reviewer` alone, trusting its own stated scope ("evaluate skills against authoritative
standards"), has no way to know from the agent's own file that description-length is out of its checked
set.

**Verification surface:** none found — no rule or check requires the two agents' rulebook-check coverage
to be reconciled or documented as complementary/non-overlapping.

Evidence origin: direct
Coverage: partial
Confidence: medium
Evidence source: `plugins/plugin-devkit/agents/skill-reviewer.md`, `plugins/plugin-devkit/agents/
consistency-reviewer.md` (both files read in full for this run; a broader survey of every other
`*-reviewer` agent's own R-number coverage was not performed and would be needed to say how widespread
this gap is beyond this one pair)
<!-- finding:end -->

## Top Actions

1. **Fix `skill-reviewer.md`'s Step 1/Step 4 to also load and apply `R21_skill_description_size`'s
   tiered thresholds**, the same way it already does for R13/R18 — this is the direct structural fix for
   the root cause behind Phase 3's agent-vs-agent conflict, not just the symptom.
2. **Reconcile the two verdicts in the transcript's own scenario**: `consistency-reviewer`'s Critical
   finding is the correct one against this repo's real, current R21 threshold (1180 > 1024) —
   `skill-reviewer`'s "no action needed" verdict should not be the one acted on if this were a real
   commit decision.
3. **Document each `*-reviewer` agent's owned subset of `plugin-rulebook`'s R-numbered checks** (or
   confirm via a wider survey that this gap is isolated to R21/skill-reviewer) so a caller dispatching one
   reviewer alone knows what is and isn't covered without needing a second, differently-worded dispatch to
   surface a Critical-severity gap.
4. **Add an explicit disclosure step when two dispatched reviewers reach contradictory verdicts on the
   same subject**, per `disclose-before-overriding-decisions.md`'s own general principle — this
   transcript shows the gap concretely: the contradiction was silently left unresolved rather than
   surfaced to the user before any commit action.

Next: run `generating-analysis-recommendations` on this report to expand its findings into a WHAT/WHY/HOW action plan.
Also: run `reviewing-analysis-findings` to cross-check these reports for duplicates or contradictions. (Mechanical trigger: `Glob` found 2 existing `this-conversation-*.md` reports — `analyzing-actor-behavior` and `analyzing-governance-and-conflicts`'s own prior run — under this same scope-slug. Per Phase 3's Session-vs-session finding above, both are actually about an unrelated real session, not this fixture, so this suggestion is offered per the skill's own mechanical scope-slug check rather than because those two reports are substantively related to this one.)
