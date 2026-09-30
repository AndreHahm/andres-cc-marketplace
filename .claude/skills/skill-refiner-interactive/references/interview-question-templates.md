# Interview Question Templates

The `AskUserQuestion` templates for the refinement workflow's interview and its two conditional asks. SKILL.md holds the flow (which question, when, and how answers route); this file holds the question text and options. Every question has 2-4 options, since the tool adds a free-text "Other" choice automatically.

## Table of Contents
1. [BATCH 1: Refinement Focus](#batch-1-refinement-focus)
2. [BATCH 2: Implementation Details](#batch-2-implementation-details)
3. [Mirror Divergence Halt](#mirror-divergence-halt)
4. [Trigger Regression Check](#trigger-regression-check)

## BATCH 1: Refinement Focus

Ask one question at a time, in order. When goals were selected, skip Question 1.

### Question 1: What aspects need improvement?

```
question: "What aspects need improvement?"
header: "Focus Areas"
multiSelect: true
options:
  - "Clarity": make instructions clearer, remove jargon, improve examples
  - "Efficiency": reduce token usage, consolidate references, optimize content
  - "Structure": reorganize sections, improve flow, better grouping
  - "User Interaction UX": convert free-form interactions to AskUserQuestion patterns
```

### Question 2: What specific problems are you seeing?

```
question: "What specific problems are you seeing?"
header: "Key Issues"
multiSelect: true
options:
  - "Hard-to-follow instructions": instructions are hard to follow
  - "Scattered references": references scattered and redundant
  - "Nested sections": too many nested sections
```

### Question 3: What would success look like?

```
question: "What would success look like?"
header: "Success"
multiSelect: false
options:
  - "Clearer workflow": instructions are easier to follow end to end
  - "Lower token cost": fewer tokens loaded per activation
  - "Production-ready": production-ready with error handling
```

### Question 4: Any areas to exclude or preserve as-is?

```
question: "Any areas to exclude or preserve as-is?"
header: "Scope Limits"
multiSelect: true
options:
  - "Keep validation gates": leave the target's validation gates and its Testing & Validation section unchanged
  - "Keep tool scoping": don't change allowed-tools, and add no tool grants
```

An empty selection, or typing "none" under the automatic "Other" choice, means nothing is excluded; the operator names anything else through "Other" too. Exclusions also bind SKILL.md step 6's auto-added standard sections. After all responses, document the approved scope and proceed to BATCH 2.

## BATCH 2: Implementation Details

Ask only the questions whose trigger was detected in pre-analysis (reference-file clusters are handled by the consolidation ask at SKILL.md step 3, not here). Each conditional question has two options, "Yes" and "No".

**Large low-frequency section** (≥50 lines, estimated <20% usage):

```
question: "Section '[NAME]' is X lines and appears in <20% of activations. Extract to references/[name].md?"
header: "Extraction"
options:
  - "Yes": CREATE reference file, LINK in SKILL.md, DELETE inline
  - "No": keep inline
```

**Intake pattern violation** (a section collects input without AskUserQuestion):

```
question: "Section '[NAME]' collects user input without AskUserQuestion ([reason]). Convert it?"
header: "Intake"
options:
  - "Yes": replace free-form intake with an AskUserQuestion block; derive options from observed inputs
  - "No": keep free-form; this section intentionally takes open-ended input
```

**R22 argument-hint/arguments mismatch:**

```
question: "Frontmatter argument-hint/arguments doesn't match what the body consumes ([mismatch]). Fix now?"
header: "Arguments"
options:
  - "Yes": update argument-hint/arguments to match body usage
  - "No": leave as-is; the end-of-workflow plugin-rulebook gate will still catch it
```

**`when_to_use` split candidate:**

```
question: "description is X characters and embeds trigger conditions inline. Split into description + when_to_use?"
header: "Desc split"
options:
  - "Yes": move the trigger-condition clause into a new when_to_use field
  - "No": keep a single description field
```

**Production hardening** (asked in every refinement session, even when no other BATCH 2 question applies):

```
question: "Which production checks should I run?"
header: "Prod checks"
multiSelect: true
options:
  - "Security scan": Grep SKILL.md, references/ and scripts/ for credentials, keys and tokens, and for ${VAR}-style substitutions that corrupt example code
  - "Error handling": verify the skill handles missing files, malformed YAML and permission errors
  - "Tool scoping": audit allowed-tools: remove unused tools, narrow Bash wildcards
  - "None needed": skip production checks for this session
```

Standard sections (Quick Start, When to Use, When NOT to Use, Testing & Validation, Reference Guide) are auto-added in SKILL.md step 6, so no question is needed for them.

## Mirror Divergence Halt

Used when a skill exists at both `plugins/<plugin>/skills/<name>/` and `<repo root>/.claude/skills/<name>/` and the two copies differ (R19). The Refinement workflow uses the four-option form below. Validation is report-only and never overwrites a copy, so it uses the two-option Validation form that follows it instead:

```
question: "Found this skill at both [path A] and [path B], but their content differs. Which is authoritative?"
header: "Mirror"
options:
  - "Show me the diff first": display what differs before deciding
  - "[path A] is correct": analyze [path A]; [path B] is overwritten with it in step 6, only if changes are applied
  - "[path B] is correct": analyze [path B]; [path A] is overwritten with it in step 6, only if changes are applied
  - "Stop": don't touch either copy; end the session so the operator can reconcile
```

Choosing a copy never edits anything at this point, so a plan-only run leaves both copies untouched.

Validation form (report-only; no overwrite option):

```
question: "Found this skill at both [path A] and [path B], but their content differs. Validation is report-only and changes nothing. How should I proceed?"
header: "Mirror"
options:
  - "Show me the diff first": display what differs, then end the session so the operator can reconcile and re-run
  - "Stop": don't touch either copy; end the session so the operator can reconcile
```

## Trigger Regression Check

Used when `description` or `when_to_use` changed, before finalizing:

```
question: "The description changed. Verify trigger accuracy didn't regress before finalizing?"
header: "Trigger eval"
options:
  - "Run trigger-eval check": delegate to Skill(skill-development) to run its description-optimization loop
  - "Quick size check only": compare the new lengths against plugin-rulebook's R21 tiers
  - "Skip": finalize without a check; fine for wording tweaks that leave trigger phrases alone
```
