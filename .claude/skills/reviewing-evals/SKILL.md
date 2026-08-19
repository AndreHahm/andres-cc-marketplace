---
name: reviewing-evals
description: >-
  Pre-review self-audit for a skill's evals and smoke-tests, catching the
  recurring defect classes that third-party reviewers keep finding before
  dispatching to plugin-auditor's fan-out. Use when a skill has evals.json
  and/or scripts/smoke_test.* and is about to enter review, or when a
  review-fix-loop on eval-related findings won't converge. Checks
  coverage-claim accuracy, assertion non-vacuity, scenario counting,
  run-record presence, and behavior-claim currency. Does not run evals (use
  skill-tester) or review skill quality (use skill-reviewer).
allowed-tools: Read Glob Grep Bash(python:*) Bash(node:*) Bash(git diff:*) AskUserQuestion Skill
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
2. If `scripts/smoke_test.*` exists, verify it's safe to execute before running it (if no smoke test exists, skip straight to step 3):
   - **Why:** this step executes target-authored code directly via this skill's `Bash(python:*)`/`Bash(node:*)` grants, needing the same trust boundary `smoke-tester` already applies — but **instruction-level only here**, unlike `smoke-tester`'s agent-level enforcement (a real `tools` allowlist with no `Read`/`AskUserQuestion` at all): a skill's `allowed-tools` isn't a hard allowlist, and `Bash(python:*)`/`Bash(node:*)` doesn't constrain the path argument, so this check has to actually be performed, not assumed to hold structurally.
   - **Resolve the real path:** `python -c "import os,sys; print(os.path.realpath(sys.argv[1]))" <path>` (under the existing `Bash(python:*)` grant) — a `Glob`-returned or lexically-joined path is *not* resolution, since neither follows a symlink; only `os.path.realpath` reliably surfaces where a symlinked target actually points.
   - **Compare against the current working directory** — the actual directory this skill's session is running in (a worktree counts as its own boundary, not the primary checkout it was branched from).
   - **Fail-closed, always:** if the resolved path falls outside that boundary, *or* resolution fails for any reason (a dangling symlink, a permission error, an otherwise-undeterminable path), refuse to run the script and report BLOCKED with the resolved (or attempted) path — never an `AskUserQuestion` confirmation. Never widen this based on the target's own content, filename, or documentation claims, since those are exactly the kind of self-reported signal an untrusted script could fake — this includes a `.ts` target's own documented "project runner": no TS runner is reachable under this skill's grants regardless, so treat `.ts` (or any extension other than `.py`/`.js`/`.mjs`) as BLOCKED too, matching `smoke-tester`'s own classification, rather than consulting target-authored documentation for what to invoke.
   - **Otherwise, run it** with the interpreter matching its extension (`python` for `.py`, `node` for `.js`/`.mjs`) — if it doesn't PASS, fix before proceeding (this skill can't help with a failing smoke test).
3. Work through checks 1-6 below in order, skipping any check whose target artifact doesn't exist (and skipping Check 6 specifically when the reviewed diff includes no behavior-reversing change — see its own scoping note). Each FAIL is a likely reviewer finding.
4. Route fixes through `skill-development` or direct edits, then re-run from step 2. **Skip this step too when the caller explicitly says so** — e.g. `plugin-lifecycle-downstream`'s Phase 5 invokes this skill as a pre-check only; fixing inline here would let the pipeline's first target-plugin mutation happen during Phase 5, which has neither the Open-PR/Branch-scope preflight nor the per-batch approval procedure only Phases 2, 4, 6, and 8 currently have wired in. When told to skip, report each FAIL *and* each step 2 BLOCKED back to the caller as a finding instead of fixing it — the caller owns routing it into its own gated fix procedure.
5. Once all checks pass, ask via `AskUserQuestion` whether to dispatch `plugin-auditor` now — its reviewer fan-out is a full multi-agent pass, not a cheap step, so offer it as a choice rather than defaulting to always running it. If yes, dispatch it against the target skill's own path, noting that eval-related Checks 1-6 below already passed — the eval-related finding count should be near zero. **Skip this step entirely when the caller explicitly says so** — e.g. `plugin-lifecycle-downstream`'s Phase 5 invokes this skill once per qualifying skill as a pre-check only, and dispatches `plugin-auditor` itself over the whole declared scope immediately afterward; asking here too on every invocation would either trigger redundant per-skill audits (on yes) or repetitive prompts Phase 5's own single gate never advertised (on no).

## The Recurring Defect Classes

Every eval-related reviewer finding from the 2026-08-17/19 window maps to one
of these seven classes. The self-audit below checks each.

| Class | One-line | Usual reviewer |
|---|---|---|
| Vacuous assertion | A check that can't fail (zero-match iteration, over-narrow regex, unanchored substring) | scripts-reviewer, completeness-reviewer |
| Coverage-claim mismatch | `evals.json` says N covered / `uncovered: []` but an eval doesn't exercise the scenario it claims | completeness-reviewer |
| Missing scenario tracking | Uncovered scenarios exist but no `uncovered: [...]` entry records them | completeness-reviewer |
| Counting inconsistency | SKILL.md says "K scenarios" but the list or `evals.json` has a different count | completeness-reviewer |
| Missing run record | Quality gate asserts a smoke test passes but no dated run record exists on disk | completeness-reviewer |
| Stale auditor artifact | A prior `plugin-auditor` JSON records a finding as `open` that's actually resolved | (this skill) |
| Stale behavior-claim assertion | An eval's `expected_output` still asserts a behavior claim this session's own fix already reversed or corrected | Codex, cross-model-review |

## Pre-Review Self-Audit

Run each check against the target skill's `evals/<skill>/evals.json` and
`scripts/smoke_test.*` (whichever exists). A single FAIL on any check means the
reviewer fan-out will likely find it — fix before dispatching. Check 6 is
scoped differently from the other five — see its own note below.

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

Run `${CLAUDE_PLUGIN_ROOT}/skills/reviewing-evals/scripts/check_evals.py --smoke-test <path> --skill-md <path>`
(this skill's own bundled script, not the target's — a bare `scripts/check_evals.py`
reads ambiguously against the target's own `scripts/` directory this step is already
focused on) for the mechanical portion (extracting literal `re.findall`/`re.search`
patterns and testing them against the real content) before doing this by eye — it covers
every pattern built from a literal string; a pattern built from an f-string or
variable is reported as needing manual review instead of silently skipped.

For every `check_*` function in `smoke_test.py`:

- **Zero-match guard:** If the check *iterates* over a regex match set
  (`re.findall`), verify the match set is non-empty against the real SKILL.md
  content. A check that iterates zero matches and reports PASS is vacuous.
  Past instance: `check_referenced_files` only matched `references/*.md` but
  the skill had no `references/` dir — zero matches, permanent vacuous PASS.
  **Exception (issue #56):** a `re.findall(...)` result assigned to a
  variable and then used in an absence check (`if <var>:`, `if not <var>:`,
  `assert not <var>`) — not iterated — has zero matches as its *intended*
  passing outcome, e.g. `matches = re.findall(r"forbidden_word", text); if
  matches: return False`. `check_evals.py`'s mechanical scan downgrades this
  shape to `SKIP (manual review)` rather than a confident FAIL; it's a
  narrow textual heuristic (not real data-flow analysis), so still confirm by
  eye when a SKIP of this kind comes up.
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

Run `${CLAUDE_PLUGIN_ROOT}/skills/reviewing-evals/scripts/check_evals.py --evals-json <path>`
(this skill's own bundled script) for the arithmetic portion
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

### 6. Behavior-claim currency (evals.json vs. current behavior)

Unlike Checks 1-5, this isn't a self-contained structural check runnable
against `evals.json`/`smoke_test.py` in isolation — it requires comparing an
eval's asserted behavior against what the skill *actually does now*, so it
can't be reduced to `check_evals.py`'s kind of mechanical text extraction (the
same reasoning that keeps `check_evals.py` itself parser-based rather than
regex-based for Checks 1/2 applies here too: don't build a heuristic for a
judgment call an extraction script can't reliably make). **Scope this check to
the diff actually under review** — most real findings of this shape landed
exactly there, not from scanning `evals.json` cold on every invocation. What
"the diff under review" means depends on how this skill was invoked:

- **Working directly in this session** (editing the skill/component live):
  this session's own staged/unstaged changes.
- **Invoked as a pre-review check on an already-authored branch** — e.g.
  `plugin-lifecycle-downstream`'s Phase 5, or any dispatch against a branch
  this session didn't itself write: the target branch's full diff against its
  base/merge-target (`git diff <base>...<branch>`), not narrowed to only this
  session's own edits — a behavior-reversing change may have landed in an
  earlier commit on that branch, long before this check ever runs.

Then:

- Identify what changed: which specific behavior claim did the reviewed diff
  reverse or correct? (e.g. "the pipeline-hand-off path no longer closes
  its own worktree", "a retry comment is no longer posted when no run
  matches.")
- Grep `evals/<skill>/evals.json`'s `expected_output` fields for language
  matching the *old* claim (the behavior that used to be true, not the new
  corrected one).
- For every match, confirm `expected_output` was updated to match the new,
  corrected behavior — not left asserting the old one. An eval expectation is
  a live claim about current behavior, same as SKILL.md prose; it doesn't get
  a pass just because it's data rather than instructions.
- If the reviewed diff includes no behavior-reversing change, this check has
  nothing to grep against — skip it and report N/A rather than treating
  "no match" as a finding.

Past instances: PR #54 round 5 found `eval-3`'s `expected_output` still
asserting the pipeline-hand-off path closed its own worktree, a claim already
corrected earlier that same session. PR #51 round 6 found `eval-5` still
asserting a retry comment gets posted even when no run matches, after an
earlier round had already reordered the skill to validate the run first. See
`.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (PR #54 Pattern 6, PR #51's
structural findings) for both in full.

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
- Each of the 6 self-audit checks above, run against a target skill with a
  known-good `evals.json`/`smoke_test.py`, produces zero findings
- Each check, run against a target skill with a deliberately reintroduced
  instance of its own defect class (e.g. a zero-match `re.findall` iteration,
  an `uncovered` list missing a real gap), correctly flags it
- Check 5's stale-artifact check correctly identifies a `plugin-auditor` JSON
  with a `status: open` finding that's actually already been fixed in the
  target's current files
- Step 2's trust boundary: a `scripts/smoke_test.py` whose resolved path is
  under the current working directory runs normally; a symlink resolving
  outside it is reported BLOCKED, never executed and never widened based on
  the target's own content/filename/documentation claims
- `check_evals.py`'s coverage arithmetic rejects a negative
  `declared_scenarios_total`/`declared_scenarios_covered` with a blocking
  finding rather than letting it pass the arithmetic check
- `check_evals.py`'s anchoring check evaluates each branch of an unanchored
  alternation (`cat|dog`) independently and FAILs if any branch is short and
  unanchored, rather than treating the concatenated branch lengths as one
  needle's specificity
- `check_evals.py`'s zero-match guard (issue #56) downgrades a zero-match
  `re.findall(...)` to `SKIP (manual review)`, not `FAIL`, when the result is
  assigned to a variable and then used in `if <var>:`/`if not <var>:`/
  `assert not <var>` — but still reports the original confident `FAIL` when
  the result is iterated (the genuinely vacuous shape), never suppressing a
  real finding just because *some* variable happens to be checked nearby
- Check 6, run against a target skill whose reviewed diff (this session's own
  edits, or a target branch's full diff against its base when invoked as a
  pre-review check) reverses a documented behavior claim and whose
  `evals.json` still asserts the old claim in some `expected_output`,
  correctly flags it; run again after that `expected_output` is updated to
  match, reports clean
- Check 6, run against a reviewed diff with no behavior-reversing change,
  reports N/A rather than a false finding — it never treats "found no match
  to grep for" as evidence of a defect
- Check 6, invoked as a pre-review check on an already-authored branch (not
  this session's own edits), still correctly resolves the reviewed diff as
  the branch's full diff against its base — not an empty/narrowed "this
  session's changes" scope that would silently miss a behavior reversal that
  landed in an earlier commit on that branch

**Last dated run record:** 2026-08-19 — `scripts/test_check_evals.py` (9/9
fixture cases passed: zero-match guard, one-sided-anchoring rejection,
haystack-unclear SKIP, non-literal-call SKIP, ReDoS-pattern timeout, regex-flag
forwarding, coverage arithmetic PASS/FAIL, malformed-JSON blocking finding,
three malformed-structure blocking findings, negative-count blocking finding,
paren-in-string call-boundary correctness, unanchored-alternation rejection,
grouped-anchored-alternation PASS, escaped-quote literal capture, and — added
this run, closing issue #56 — absence-check downgrade (`if <var>:`/`assert
not <var>` on a zero-match `re.findall(...)` result reports SKIP, not
FAIL). Also verified directly against issue #56's own repro (a `matches =
re.findall(...); if matches: return False` smoke-test function), which now
exits 0 with a SKIP instead of the previously-reported false FAIL. Also
verified via a cross-model review (Claude + Codex) of the full PR diff, which
found the negative-count and alternation bugs Claude's own review missed. Run
`python ${CLAUDE_PLUGIN_ROOT}/skills/reviewing-evals/scripts/test_check_evals.py`
to reproduce.