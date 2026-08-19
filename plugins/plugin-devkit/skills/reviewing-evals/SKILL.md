---
name: reviewing-evals
description: >-
  Pre-review self-audit for a skill's evals and smoke-tests, catching the
  recurring defect classes that third-party reviewers keep finding before
  dispatching to plugin-auditor's fan-out. Use when a skill has evals.json
  and/or scripts/smoke_test.* and is about to enter review, or when a
  review-fix-loop on eval-related findings won't converge. Checks
  coverage-claim accuracy, assertion non-vacuity, scenario counting, and
  run-record presence. Does not run evals (use skill-tester) or review skill
  quality (use skill-reviewer).
allowed-tools: Read Glob Grep Bash(python:*) Bash(node:*) AskUserQuestion Skill
---

# Eval Review Self-Audit

**Purpose:** Collapse the eval-related review-fix-loop. Most third-party
reviewer findings on new skills are eval/smoke-test defects that a pre-flight
self-check could have caught. This skill runs that self-check *before* the
reviewer fan-out, so the common defect classes are fixed locally in one pass
instead of over multiple review rounds.

## When to Use

- Before dispatching `plugin-auditor` against a skill that has `evals/<skill>/evals.json` and/or `scripts/smoke_test.*`
- When a review-fix-loop on eval-related findings (vacuous assertions, coverage-claim mismatches, missing scenarios) won't converge
- After editing `evals.json` or `smoke_test.*`, to verify the edit didn't introduce a known defect class

## When NOT to Use

- **Running evals or benchmarking** — use `skill-tester` (it executes evals with_skill vs baseline; this skill only checks their structure)
- **Reviewing skill quality** — use `skill-reviewer` (structure, content, clarity; this skill checks eval artifacts only)
- **Fixing eval defects** — this skill finds and reports; route fixes through `skill-development` or direct edits, then re-run this check

## Quick Start

1. Identify the target skill; locate its `evals/<skill>/evals.json` and `scripts/smoke_test.*` (either may be absent — this skill only checks whichever exists).
2. If `scripts/smoke_test.*` exists, run it with the interpreter matching its extension (`python` for `.py`, `node` for `.js`/`.mjs`; if `.ts` with no documented project runner, skip this step and note it — same convention as the `smoke-tester` agent) — if it doesn't PASS, fix before proceeding (this skill can't help with a failing smoke test). If no smoke test exists, skip to step 3.
3. Work through checks 1-5 below in order, skipping any check whose target artifact doesn't exist. Each FAIL is a likely reviewer finding.
4. Route fixes through `skill-development` or direct edits, then re-run from step 2.
5. Once all checks pass, ask via `AskUserQuestion` whether to dispatch `plugin-auditor` now — its reviewer fan-out is a full multi-agent pass, not a cheap step, so offer it as a choice rather than defaulting to always running it. If yes, dispatch it against the target skill's own path, noting that eval-related Checks 1-5 below already passed — the eval-related finding count should be near zero.

## The Recurring Defect Classes

Every eval-related reviewer finding from the 2026-08-17/18 window maps to one
of these six classes. The self-audit below checks each.

| Class | One-line | Usual reviewer |
|---|---|---|
| Vacuous assertion | A check that can't fail (zero-match iteration, over-narrow regex, unanchored substring) | scripts-reviewer, completeness-reviewer |
| Coverage-claim mismatch | `evals.json` says N covered / `uncovered: []` but an eval doesn't exercise the scenario it claims | completeness-reviewer |
| Missing scenario tracking | Uncovered scenarios exist but no `uncovered: [...]` entry records them | completeness-reviewer |
| Counting inconsistency | SKILL.md says "K scenarios" but the list or `evals.json` has a different count | completeness-reviewer |
| Missing run record | Quality gate asserts a smoke test passes but no dated run record exists on disk | completeness-reviewer |
| Stale auditor artifact | A prior `plugin-auditor` JSON records a finding as `open` that's actually resolved | (this skill) |

## Pre-Review Self-Audit

Run each check against the target skill's `evals/<skill>/evals.json` and
`scripts/smoke_test.*` (whichever exists). A single FAIL on any check means the
reviewer fan-out will likely find it — fix before dispatching.

### 1. Assertion non-vacuity (smoke_test.py)

Scoped to Python (`re.findall`/`re.search`) smoke tests specifically — the
defect classes below are drawn from real Python instances. A JS/TS smoke test
can have analogous vacuous-assertion bugs (e.g. an empty-array `.filter()`
that silently reports pass), but this check hasn't been validated against
that case yet; apply the "can it fail" test at the bottom manually if the
target's smoke test isn't Python.

The zero-match-guard and anchored-matching checks below are intentionally-duplicated,
fast local copies of `scripts-reviewer`'s Check 1/6 (zero-match iteration,
overly-broad matching), scoped to eval/smoke-test scripts specifically so they can run
before dispatch instead of waiting for the fan-out. If `scripts-reviewer`'s own check
definitions change, revisit these too — they're not derived from a shared source, so
they can drift independently.

Run `scripts/check_evals.py --smoke-test <path> --skill-md <path>` for the
mechanical portion (extracting literal `re.findall`/`re.search` patterns and
testing them against the real content) before doing this by eye — it covers
every pattern built from a literal string; a pattern built from an f-string or
variable is reported as needing manual review instead of silently skipped.

For every `check_*` function in `smoke_test.py`:

- **Zero-match guard:** If the check iterates over a regex match set
  (`re.findall`), verify the match set is non-empty against the real SKILL.md
  content. A check that iterates zero matches and reports PASS is vacuous.
  Past instance: `check_referenced_files` only matched `references/*.md` but
  the skill had no `references/` dir — zero matches, permanent vacuous PASS.
- **Anchored matching:** Every `re.search` needle must be word-boundary
  anchored (`\b` + `re.escape(needle)` + `\b`) or full-string matched. An
  unanchored search for a short/common-word needle (e.g. `cat`) false-passes
  on unrelated prose (`location`, `classification`).
- **Path-prefix preservation:** A file-existence check must not strip
  prefixes in a way that erases the distinction between a correct path and a
  broken one. Past instance: stripping any prefix before `prompts/` made a
  broken `${CLAUDE_PLUGIN_ROOT}/prompts/review.md` (plugin root, doesn't
  exist) indistinguishable from a correct `skills/<skill>/prompts/review.md`.
- **The "can it fail" test:** For each check, mentally construct the input
  that would make it FAIL. If you can't, the check is vacuous.

### 2. Coverage-claim accuracy (evals.json)

If `evals.json` exists but fails to parse as JSON, report that directly as its
own blocking finding — don't attempt Checks 2/3 against unparseable content,
and don't silently skip them as if the file were simply absent.

Field names below are `evals.json`'s own `testing_validation_coverage` object,
owned and schema-defined by `skill-tester`'s `references/eval-schema.md` — read
that file if a field's meaning is unclear rather than trusting this restatement,
since this section can drift out of sync with the schema it describes.

Run `scripts/check_evals.py --evals-json <path>` for the arithmetic portion
(`declared_scenarios_covered` + `len(uncovered)` == `declared_scenarios_total`,
plus a JSON-parse check) — it's purely mechanical, no need to do it by hand.
The scenario-exercised-by-which-eval judgment below still needs a human read.

- Read every eval's `prompt` and `expected_output` in `evals/<skill>/evals.json`.
- For each scenario counted in `testing_validation_coverage.declared_scenarios_covered`,
  confirm at least one eval's prompt actually exercises that scenario (not an
  adjacent one). Past instance: eval 2's prompt stipulated codex-kit WAS installed
  (scenario 3: `isolation_profile_unavailable`), but coverage claimed it
  covered scenario 2 (genuinely missing) — scenario 2 had no eval.
- Confirm `declared_scenarios_covered` + `len(uncovered)` ==
  `declared_scenarios_total`.
- Confirm every `uncovered: [...]` entry is a real gap, not a scenario that
  an eval actually exercises.

### 3. Counting consistency (SKILL.md vs evals.json)

- If SKILL.md names a scenario count (e.g. "7 quality-gate scenarios"),
  confirm it matches `evals.json`'s `declared_scenarios_total`. Watch for
  off-by-one when a smoke-test-passes tooling gate is counted as a "scenario"
  in one place but not another.

### 4. Run-record presence

- If SKILL.md asserts a smoke test passes and should be re-run after edits,
  confirm a dated run record exists (in SKILL.md's Test section or a changelog
  entry). Absence of evidence is not evidence it never ran, but a reviewer will
  flag it.
- If SKILL.md claims eval coverage, confirm actual run evidence exists on disk
  — not just `evals.json`'s static scenario definitions. Look for a completed
  `benchmark.json` under `evals/<skill>/workspace/iteration-N/` (Full Pipeline)
  or a `grading.json` under `workspace/iteration-N/eval-M/{with_skill,baseline}/`
  (Quick Workflow). This is the same evidence tier `plugin-grader`'s own rubric
  (`references/rubric.md`) checks for its testing dimension: `evals/` +
  `evals.json` present with no `benchmark.json`/`grading.json` scores as
  "exists, no run evidence" — not full credit — even though the static files
  look complete.

### 5. Stale auditor artifacts

- If a prior `.claude/output/plugin-auditor/<skill>-*.json` exists, re-verify
  each `status: open` finding against current repo state. Fix or supersede
  the artifact before the next review round — a reviewer re-finding an
  already-resolved issue wastes a round.
- If the file exists but fails to parse as JSON, or parses without a `status`
  field on its findings, report it as an unreadable artifact rather than
  silently treating it the same as "no prior artifact" — a corrupt audit
  record is itself worth flagging, not skipping past.

## Testing & Validation

**Verify this skill activates on:**
- "review these evals before I send this to plugin-auditor"
- "check this skill's evals.json/smoke_test.py for known defect classes"
- "why does the review-fix loop on eval findings keep failing"

**Verify it does NOT activate on:**
- "run the evals for this skill" → use `skill-tester`
- "review this skill's quality/structure" → use `skill-reviewer`
- "audit this whole plugin" → use `plugin-auditor`

**Quality gates:**
- Each of the 5 self-audit checks above, run against a target skill with a
  known-good `evals.json`/`smoke_test.py`, produces zero findings
- Each check, run against a target skill with a deliberately reintroduced
  instance of its own defect class (e.g. a zero-match `re.findall` iteration,
  an `uncovered` list missing a real gap), correctly flags it
- Check 5's stale-artifact check correctly identifies a `plugin-auditor` JSON
  with a `status: open` finding that's actually already been fixed in the
  target's current files

**Last dated run record:** 2026-08-19 — `scripts/test_check_evals.py` (5/5
fixture cases passed: zero-match guard, unanchored-match guard, coverage
arithmetic PASS, coverage arithmetic FAIL, malformed-JSON blocking finding).
Run `python scripts/test_check_evals.py` to reproduce.