# Testing-Mandate Rules: R28-R31 Full Detail

Full check procedures, config shapes, and worked examples for R28-R31 — kept here rather than inline in
`SKILL.md` per the same delegation pattern R13/R18/R21/R23-R26 already use (a one-line summary plus
**Scope** stays in `SKILL.md`; the full mechanics live here).

**Rollout scope, shared by R28-R30:** forward-looking only — applies to newly-created or
structurally-modified skills, not the pre-existing backlog. Same precedent as
`.claude/rules/require-declared-plugin-language.md`. R31 is the one exception (see its own section
below): it checks correctness of content that already exists, not whether content exists at all, so the
rollout exemption does not apply to it.

## R28 — Skill Testing Mandate, Full Detail

Reuses `plugin-grader/references/rubric.md`'s existing testing-dimension tiers verbatim instead of
inventing a second threshold system — that rubric already distinguishes "evals exist with run evidence"
from "evals exist, never run."

**Check (forward-looking — newly-created or structurally-modified skills only):**

- **PASS:** `evals/<skill>/evals.json` exists, meets `config.min_eval_scenarios`, **and** has actual run
  evidence on disk — a completed `benchmark.json` under `evals/<skill>/workspace/iteration-N/`, or
  `grading.json` under `workspace/iteration-N/eval-M/{with_skill,baseline}/` (the same evidence tier
  `reviewing-evals` Check 4 already looks for).
- **PASS (alternate path):** no `evals.json`, but the skill's `## Testing & Validation` section (R29)
  contains an explicit sentence justifying why full evals aren't warranted (e.g. "this skill is a thin
  wrapper with no branching logic; smoke-tested via X instead").
- **ADVISORY (not blocking):** `evals.json` exists but has no run evidence yet, **or** has run evidence
  but under `config.min_eval_scenarios` — the count itself is `guide`-tier per the source below, not
  platform-enforced, so an under-count is a flag, not a block.
- **FAIL (REQUIRED):** neither `evals.json` nor a justification note exists at all, and the skill isn't
  in the pre-existing forward-looking-exempt backlog. Only total absence of both paths blocks.

**Source for `min_eval_scenarios: 3`:** `platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices`
(canonical; `docs.claude.com` 302-redirects there), "Checklist for effective Skills" → Testing: "At least
three evaluations created." Tracked as `skill-authoring-evaluations-guidance` in
`upstream-sources-registry/assets/sources.json` (`custom: true`, `authority: guide`,
`volatility: evolving`). This is `guide`-tier, not `spec`-tier — the source page itself states there is
no built-in way to run these evaluations, so per `references/classification-criteria.md` a `guide`-tier
source backs an `ADVISORY`-severity threshold, not a blocking `REQUIRED` one. It is Anthropic's general
Agent Skills guide, not Claude-Code-specific, though it applies equally to plugin-devkit skills. The
source page's own example eval JSON shape (`skills`/`query`/`files`/`expected_behavior`) is illustrative
only — it is not `skill-tester`'s actual schema (`prompt`/`expected_output`/`testing_validation_coverage`).

**Config shape:**
```json
"config": {
  "min_eval_scenarios": 3,
  "min_eval_scenarios_severity": "ADVISORY",
  "run_evidence_required_paths": ["workspace/iteration-*/benchmark.json", "workspace/iteration-*/eval-*/*/grading.json"]
}
```

## R29 — Skill Testing Section Required, Full Detail

**Checked by substance, not exact heading wording — corrected 2026-08-27.** The original design
canonicalized one specific phrasing ("Verify this skill activates on:"/"Verify it does NOT activate
on:"), on the premise that it was already used consistently across the plugin. A live compliance check
run while wiring R28-R32 into 5 pre-existing skills (including `plugin-rulebook` itself) found the
premise wrong: the plugin is split exactly 4-vs-4 between that phrasing and an older "Expected
triggers:"/"Non-triggers:" convention, with no dominant convention either way. Forcing a rewrite of
already-adequate content to match one arbitrarily-chosen wording would be exactly the kind of
low-value churn this rulebook's own governing CLAUDE.md warns against — the rule's actual purpose is
ensuring concrete positive/negative trigger examples and checkable pass criteria exist, not enforcing
one specific heading string.

**Check (forward-looking):** `SKILL.md` must contain a `## Testing & Validation` heading (exact text,
case-sensitive) containing at minimum:
- A positive-trigger-example subsection with concrete trigger-phrase examples — either
  "Verify this skill activates on:" or "Expected triggers:" (see
  `config.accepted_positive_trigger_headings` for the full accepted set)
- A negative-trigger-example subsection with concrete negative examples — either
  "Verify it does NOT activate on:" or "Non-triggers:" (see `config.accepted_negative_trigger_headings`)
- A checkable-pass-criteria subsection — "Quality gates:" (see `config.accepted_pass_criteria_headings`)
- "Last dated run record:" — required only when `evals/` or `scripts/smoke_test.*` exists for that
  skill; a skill with neither has nothing to record a run of yet, so requiring the line unconditionally
  would just produce boilerplate "N/A"

A skill using a genuinely different phrasing not yet in the accepted-headings config, but that clearly
serves the same purpose (a positive-example list, a negative-example list, checkable criteria), is an
ADVISORY finding to add the phrasing to config — not an automatic REQUIRED FAIL for using different
words.

**FAIL condition:** heading present but stub-only (a single sentence with no sub-structure) — the same
"can it fail" non-vacuity standard `reviewing-evals` Check 1 already applies to smoke-test assertions,
applied here to the section's own substance instead of a regex.

## R30 — Eval Samples Extracted, Full Detail

Categorical, not size-based. A line-count threshold (reusing R18's tiers) is the wrong tool: R18 governs
fenced *code* blocks specifically, while eval-scenario content is often prose (a scenario walkthrough, a
prompt/expected-output pair) that may not be in a code block at all. Tying the check to R29's own
boundary avoids inventing a new number:

- **R29 already defines what's allowed to stay inline** — the trigger-phrase lists, short by
  construction.
- **The check is structural:** does `SKILL.md` contain a full eval/test-scenario walkthrough (a worked
  prompt → expected-output pair, or a multi-step scenario narrative) *beyond* R29's required lists? If
  yes: REQUIRED, move it to `references/<topic>.md` (or into `evals.json` itself if it's meant to be an
  executable scenario — that's the R28 path, not R30's).
- **Duplication is the other trigger:** content in `SKILL.md` that restates a scenario already present
  in `evals.json` verbatim or near-verbatim is always flagged, regardless of size.

Naming for the extracted file follows `naming-conventions.md`'s topic-noun-phrase convention (e.g.
`references/test-scenarios.md`, not `references/testing.md` — too generic per R10).

**Severity:** `REQUIRED`, not `TIERED` — the check is categorical (yes/no), so there is no borderline
case needing a soft-warning tier.

## R31 — Eval Fixture Integrity, Full Detail

**Not forward-looking — applies immediately to any existing `evals.json`/`smoke_test.*`.** This checks
correctness of content that already exists, not whether content exists at all.

**Mechanism: dispatched from `plugin-auditor`, not `plugin-rulebook-checker`.** `plugin-rulebook-checker`
(agent) carries zero `Bash` grants of any kind — adding one here would be a first-time, broad new
capability on an agent that has never had shell access. `plugin-auditor` (skill) already carries
narrowly-scoped per-script `Bash` grants in this exact shape (`Bash(node .../bridge-invoke.mjs:*)`,
`Bash(node .../guarded-dispatch.mjs:*)`). `plugin-auditor` runs `reviewing-evals/scripts/check_evals.py`
directly as an additional fan-out step (alongside dispatching `plugin-rulebook-checker` for R1-R32) and
folds the result into the same evidence schema — see `plugin-auditor/SKILL.md` Step 4a. **The Bash grant
and Step 4a's own invocation must anchor the script by its full repo-relative path
(`Bash(python plugins/plugin-devkit/skills/reviewing-evals/scripts/check_evals.py:*)`), not a
wildcard-prefixed bare filename — `plugin-auditor` runs against untrusted target plugins as its normal
job, so an unanchored pattern risks resolving to a same-named file inside an adversarial target instead
of this plugin's own trusted script (found by the mandatory security review this gate required before
shipping, per `.claude/rules/require-security-review-before-new-gate.md`).** This still requires the same
trust-boundary path-resolution discipline `reviewing-evals` Step 2 already documents (resolve the real
path, verify inside the current working directory, fail-closed on any ambiguity).

**Check (REQUIRED, immediate):**
- `check_evals.py --smoke-test <path> --skill-md <path>`: zero-match guard, anchored-matching check →
  FAIL on a vacuous assertion or unanchored short-needle search.
- `check_evals.py --evals-json <path>`: JSON-parse validity,
  `declared_scenarios_covered + len(uncovered) == declared_scenarios_total` arithmetic → FAIL on parse
  failure or arithmetic mismatch.
- Coverage-claim accuracy's *judgment* component (does an eval's prompt actually exercise the scenario
  it claims) stays a human/`plugin-auditor`-fan-out check, per `reviewing-evals`'s own design — not
  mechanically verifiable, not part of this rule.
