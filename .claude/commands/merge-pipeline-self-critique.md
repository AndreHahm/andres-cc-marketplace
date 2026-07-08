---
description: Run SWOT analysis and self-critique over a completed /merge-pipeline run. Surfaces bugs, missed context, suboptimal decisions, and recommended optimizations across all steps. Invoke after /merge-pipeline completes.
---

# /merge-pipeline-self-critique

## Purpose

Perform a SWOT analysis and structured self-critique over a completed `/merge-pipeline` run. Read all pipeline artifacts from the run directory, evaluate each step for bugs, missed context, suboptimal decisions, and process gaps, and write `self-critique.md` to the run directory.

## When to Invoke

- Automatically after Step 5 of every `/merge-pipeline` run
- Manually against any existing run directory at any time

## Inputs

Required:

```text
run_dir: <.claude/output/<slug>-<YYYY-MM-DD>>
```

Optional:

```text
depth: concise | standard | detailed
scope: all | assessment | merge | review | documentation
skip_if_no_issues: false | true
```

Defaults: `depth=standard`, `scope=all`, `skip_if_no_issues=false`

## Workflow

### Phase 1 — Load Artifacts

Read from `run_dir`: `manifest.md`, `assessment.md`, `merge-report.md`, `review-report.md`, `documentation.md`, and `backup/`. Mark each as `present`, `missing`, or `incomplete`.

If `manifest.md` is missing or no steps are marked complete, report: _"No completed pipeline run found in `<run_dir>`. Self-critique cannot proceed."_ and stop.

If a required artifact is missing, mark the corresponding critique phase as `data-missing` and continue with available data.

### Phase 2 — SWOT Analysis

Evaluate the entire pipeline run as a unit using the four SWOT categories.

**Strengths** — look for evidence of:
- Correct relationship classification and suitability score
- All must-preserve items satisfied in the merge report
- No context loss flagged in the review report
- All conflicts explicitly resolved with documented rationale
- Clean lint pass
- Review self-rating of `excellent` or `good`
- Complete, accurate, and standalone documentation

**Weaknesses** — look for evidence of:
- Must-preserve items that are partially satisfied or not verified
- Unresolved conflicts or ambiguous decisions
- Thin, repetitive, or contradictory sections in the merged file
- Metadata changed without documented rationale
- Examples that no longer match merged behavior
- Safety rules weakened relative to source files
- High-priority open points left without an owner in documentation

**Opportunities** — look for evidence of:
- Safe optimizations from the review report that were not applied
- Missing cross-links or navigation aids in the merged file
- Better deduplication possible in the merged body
- Scope guards that could be tightened
- Model or permission decisions that could be revisited or documented more clearly

**Threats** — look for evidence of:
- Inlined references that will become stale (e.g., CLAUDE.md, external standards)
- Source files still present alongside the merged artifact, creating version conflict risk
- Open points with no owner or no resolution path
- Known divergence paths between agent or config directories
- No test or validation plan for the merged artifact's behavior

### Phase 3 — Step-Level Self-Critique

For each completed step, apply targeted critique questions and assign a step rating:

```text
no issues | minor issues | significant issues | data missing
```

**Step 1 — Assessment**
- Correct relationship classification?
- All hard conflicts identified? Any missed?
- Suitability score consistent with the actual merge outcome?
- Human Decision Required triggers complete and accurate?
- Must preserve / Must resolve / Must not items comprehensive?
- Recommended strategy matched the actual result?

**Step 1.5 — Backup**
- All source files backed up?
- Filename collisions handled correctly?
- Backup sufficient to restore from without re-running the pipeline?

**Step 2 — Merge**
- All Must preserve items verifiably present in the merged artifact?
- All Must resolve conflicts given explicit decisions with rationale?
- No Must not items violated?
- Output contracts preserved for all source files?
- Frontmatter normalized correctly with no silent changes?
- Any signs of undetected context loss?
- Examples updated to match merged behavior?

**Step 2.5 — Lint**
- YAML validity, heading hierarchy, empty sections, and unclosed fences all checked?
- Any lint findings resolved before the review proceeded?

**Step 3 — Review**
- Every assessment compliance item checked and assigned a status?
- Unit-level source coverage complete for each source file?
- Runtime and metadata decisions verified?
- Safety review thorough for this artifact type?
- Self-review rating justified by the evidence in the report?
- Required fixes identified and not silently accepted?

**Step 4 — Documentation**
- Documentation accurately describes the merged artifact?
- Usage instructions practical and immediately executable?
- All open points documented with impact, owner, and resolution path?
- Maintenance notes include which sections are runtime-sensitive?
- Documentation stands alone without reopening the merge conversation?

### Phase 4 — Issue Register

For each issue found, record a structured entry:

```text
ID: CRITIQUE-NNN
Step: <step where the issue was found>
SWOT: Weakness | Threat | Opportunity
Severity: Critical | High | Medium | Low | Info
Description: <one factual sentence>
Evidence: <artifact name and section>
Impact: <one sentence on what can go wrong>
Recommendation: <one sentence suggested action>
```

Severity scale:

- **Critical** — would cause incorrect behavior or context loss in real use
- **High** — materially reduces quality, safety, or maintainability
- **Medium** — moderate quality gap; address before next use
- **Low** — minor; optional improvement
- **Info** — observation only; no action required

### Phase 5 — Overall Rating

Rate on three dimensions and assign a verdict:

```text
Process quality:   excellent | good | acceptable | needs improvement | unacceptable
Merge quality:     excellent | good | acceptable | needs improvement | unacceptable
Documentation:     excellent | good | acceptable | needs improvement | unacceptable
```

Verdicts:

```text
PIPELINE RUN PASSED                — no significant issues
PIPELINE RUN PASSED WITH NOTES     — minor issues; acceptable for use
PIPELINE RUN NEEDS IMPROVEMENT     — significant issues; address before relying on the merged artifact
PIPELINE RUN HAS CRITICAL ISSUES   — critical or high issues found; do not use without fixes
```

### Phase 6 — Write Report and Update Manifest

Write `self-critique.md` to `run_dir` using this structure:

```markdown
# Pipeline Self-Critique

**Run:** <run_dir>
**Date:** <YYYY-MM-DD>
**Verdict:** <verdict>

## SWOT Summary

| Category | Key Points |
|---|---|
| Strengths | ... |
| Weaknesses | ... |
| Opportunities | ... |
| Threats | ... |

## Step-Level Critique

| Step | Rating | Summary |
|---|---|---|
| 1 — Assessment | ... | ... |
| 1.5 — Backup | ... | ... |
| 2 — Merge | ... | ... |
| 2.5 — Lint | ... | ... |
| 3 — Review | ... | ... |
| 4 — Documentation | ... | ... |

## Issue Register

| ID | Step | SWOT | Severity | Description | Recommendation |
|---|---|---|---|---|---|

## Overall Ratings

| Dimension | Rating |
|---|---|
| Process quality | ... |
| Merge quality | ... |
| Documentation | ... |

## Verdict

<overall verdict and one-paragraph justification>
```

Update `manifest.md` to add:

```markdown
| `/merge-pipeline-self-critique` | ✅ complete | `self-critique.md` | YYYY-MM-DD |
```

## Safety Rules

- Never modify the merged artifact, source files, or any existing pipeline artifact.
- Only writes `self-critique.md` and updates `manifest.md`.
- Does not re-run any pipeline steps.
- Does not make merge decisions or apply changes.
- If `skip_if_no_issues=true` and no issues are found, write a minimal `self-critique.md` with the verdict only and skip the Issue Register.

## Output Contract

Always produces `self-critique.md` in `run_dir`. Always updates `manifest.md`. Read-only with respect to all other pipeline artifacts.
