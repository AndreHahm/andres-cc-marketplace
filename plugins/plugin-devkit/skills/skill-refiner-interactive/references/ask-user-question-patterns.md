# AskUserQuestion Patterns & Best Practices

Use this guide when creating skills that interact with users. AskUserQuestion is the primary tool for gathering input; the patterns here keep questions valid against the tool's schema and pleasant to answer.

## Table of Contents
1. [Core Constraints](#core-constraints)
2. [Pattern 1: Single Question with Predefined Options](#pattern-1-single-question-with-predefined-options)
3. [Pattern 2: Multiple Selection](#pattern-2-multiple-selection)
4. [Pattern 3: Progressive Disclosure (Wizard Pattern)](#pattern-3-progressive-disclosure-wizard-pattern)
5. [Pattern 4: Free-Text Answers](#pattern-4-free-text-answers)
6. [Pattern 5: Conditional Questions](#pattern-5-conditional-questions-based-on-previous-answer)
7. [Pattern 6: Multi-Question Batch](#pattern-6-multi-question-batch-all-asked-together)
8. [Pattern 7: Uncertainty Option](#pattern-7-uncertainty-option)
9. [Decision Tree: Which Pattern to Use?](#decision-tree-which-pattern-to-use)
10. [Common Mistakes to Avoid](#common-mistakes-to-avoid)
11. [Best Practices Checklist](#best-practices-checklist)
12. [Verification Patterns](#verification-patterns-for-skill-refinement)

## Core Constraints

The tool schema enforces all of these; a violation is rejected, so the question never reaches the user.

| Constraint | Limit |
|------------|-------|
| Options per question | 2 to 4 (at least 2, at most 4) |
| Questions per call | 1 to 4 |
| `header` | short chip label (12 characters at most) |
| Option `label` | concise, 1-5 words |
| Free-text answer | always available: the tool adds an "Other" choice automatically, so never list one yourself |

These limits come from the tool's current schema; if the tool's own definition in your environment states different limits, follow that definition.

```json
{ "questions": [{
  "question": "...", "header": "...",
  "options": [ /* 2 to 4 items */ ],
  "multiSelect": false
}]}
```

**Violation impact:** a schema rejection, so the user never sees the question and the workflow step fails. **Fix:** split into several questions or calls, or cut options.

---

## Pattern 1: Single Question with Predefined Options

**Use when:** the user must choose ONE thing from a fixed set (2-4 options).

```json
{ "question": "What would you like to do with this skill?", "header": "Action",
  "options": [
    { "label": "Refine", "description": "Improve clarity, structure, or token usage" },
    { "label": "Validate", "description": "Check production readiness" }
  ],
  "multiSelect": false }
```

---

## Pattern 2: Multiple Selection

**Use when:** the user selects MULTIPLE things from a set (2-4 options total).

```json
{ "question": "Which core components will the plugin include?", "header": "Components",
  "options": [
    { "label": "Skills", "description": "Reusable instructions" },
    { "label": "Agents", "description": "Specialized subagents" },
    { "label": "Hooks", "description": "Event-driven scripts" }
  ],
  "multiSelect": true }
```

---

## Pattern 3: Progressive Disclosure (Wizard Pattern)

**Use when:** you need more than 4 options OR several related questions.

**Key rule:** ask ONE batch, wait for the response, THEN ask the next batch.

```
Batch 1: ask the first set of questions (up to 4 options each)
   ↓
[WAIT for response]
   ↓
Batch 2: ask follow-ups (conditional or the next step)
   ↓
[WAIT for response]
   ↓
Batch 3: continue as needed
```

**Why this matters:**
- Avoids cognitive overload (users see one question at a time)
- Allows conditional routing (skip questions based on previous answers)
- Respects the 4-option maximum (split across questions)
- Feels conversational, not like a form

**Example: six candidate components need two batches.**

Batch 1 offers the four most likely components with `multiSelect: true`. After the answer, batch 2 offers the remaining two:

```json
{ "question": "Also include either of these components?", "header": "More",
  "options": [
    { "label": "LSP servers", "description": "Language Server Protocol support" },
    { "label": "Commands", "description": "Slash-command components" }
  ],
  "multiSelect": true }
```

---

## Pattern 4: Free-Text Answers

**Use when:** the user provides free text, not a choice.

The schema does not allow an empty `options` array, so there is no "open-form" question. Instead, offer 2-4 likely answers and let the user type anything else through the automatic "Other" choice:

```json
{ "question": "What specific problems are you seeing?", "header": "Key Issues",
  "options": [
    { "label": "Hard-to-follow instructions", "description": "Instructions are unclear or out of order" },
    { "label": "Scattered references", "description": "Reference files are spread out and redundant" },
    { "label": "Nested sections", "description": "Too many levels of nested sections" }
  ],
  "multiSelect": true }
```

Derive the options from what the operator has already said or from what pre-analysis found. When nothing can be predicted, ask the question in plain text, since a reply then needs no structured choice. Reserve this for genuinely unbounded input.

---

## Pattern 5: Conditional Questions (Based on Previous Answer)

**Use when:** the next question depends on the previous answer.

```
Ask Question 1 (predefined options)
  ↓
[WAIT for response]
  ↓
IF "Option A" → ask the follow-up for Option A
IF "Option B" → ask the follow-up for Option B
IF "Option C" → skip to step X
```

**Example: an action router.**

```
Q1: "What do you want to do?"
  - "Create a new skill"         → route to the requirements interview
  - "Convert a slash command"   → route to the conversion workflow

Q2 (depends on Q1):
  IF "Create":  ask "What's the skill's purpose?"
  IF "Convert": ask "Where is the slash command?"
```

---

## Pattern 6: Multi-Question Batch (All Asked Together)

**Use when:** several related questions can all be answered together (NOT conditional).

**Key rules:**
- Each question must be independent of the others' answers
- A call carries at most 4 questions
- Every question needs 2-4 options

```json
{ "questions": [
  { "question": "Which tone fits?", "header": "Tone", "options": [ /* 2-4 */ ], "multiSelect": false },
  { "question": "Which length?", "header": "Length", "options": [ /* 2-4 */ ], "multiSelect": false }
]}
```

**When NOT to use:**
- If the next question depends on a previous answer (use conditional routing)
- If some questions should be skipped (use conditional routing)
- If you have more than 4 questions (split across calls)

---

## Pattern 7: Uncertainty Option

**Use when:** a question requires domain judgment the user may not confidently have — category selection, architecture tradeoffs, tool choices. Routine yes/no or preference questions don't need it, since adding it everywhere dilutes the 4-option budget.

```json
{ "question": "Which category best fits this skill?", "header": "Category",
  "options": [
    { "label": "Option A", "description": "..." },
    { "label": "Option B", "description": "..." },
    { "label": "I'm not sure", "description": "Infer from earlier answers, or run a short clarifying step" }
  ],
  "multiSelect": false }
```

**Why this matters:** without an explicit "I'm not sure" option, a user facing a genuine judgment call is forced to guess, and a wrong guess propagates into every downstream decision built on it.

**Handling the answer:** when selected, either infer the answer from context already gathered, or run a short clarifying step before re-asking. Don't leave the field blank and proceed.

---

## Decision Tree: Which Pattern to Use?

```
Does the user select from a fixed set?
  ├─ YES, 2-4 options, single answer   → Pattern 1
  ├─ YES, 2-4 options, multiple answers → Pattern 2
  ├─ YES, more than 4 options          → Pattern 3 (split into batches)
  └─ NO, free-text input               → Pattern 4 (2-4 likely answers + automatic Other)

Are next questions conditional on previous answers?
  ├─ YES → Pattern 5 (conditional routing between calls)
  └─ NO, all independent → Pattern 6 (one batch, at most 4 questions)
```

---

## Common Mistakes to Avoid

### Mistake 1: More than 4 options in one question

```json
// WRONG - rejected by the schema
{ "question": "Pick one:",
  "options": [ {"label":"A"}, {"label":"B"}, {"label":"C"}, {"label":"D"}, {"label":"E"} ] }
```

**Fix:** split into 2+ questions, or reduce to 4 or fewer options.

### Mistake 2: More than 4 questions in one call

```json
// WRONG - rejected: a call allows at most 4 questions
{ "questions": [ {"question":"Name?"}, {"question":"Email?"}, {"question":"Phone?"},
                 {"question":"Company?"}, {"question":"Role?"} ] }
```

**Fix:** ask progressively, at most 4 questions per call: a batch of independent ones, wait, then the next batch (conditional ones only after the answers they depend on).

### Mistake 3: An empty or one-option `options` array

```json
// WRONG - the schema requires 2 to 4 options
{ "question": "What's the skill's purpose?", "options": [] }
```

**Fix:** follow Pattern 4: offer 2-4 likely answers and rely on the automatic "Other" for typed input.

### Mistake 4: Conditional logic in a single call

```json
// WRONG - a call cannot branch on its own answers
{ "questions": [ { "question": "Create or refine?" },
                 { "question": "[conditional follow-up]" } ] }
```

**Fix:** use separate calls: ask "Create or refine?", wait, then ask the follow-up that matches the answer.

### Mistake 5: Recommending a follow-up action in prose instead of gating it

```
// WRONG - states a suggestion and waits for the user to notice and reply
"If you want, you could run `enhancement-suggestor` against this report
for a prioritized action plan."
```

The user has to notice the suggestion, decide, and type a reply in a new turn, versus getting an immediate yes/no decision in the same turn. The mistake shipped once in this toolkit and was copied across many components before it was replaced with an interactive prompt.

**Fix:** any "here's a recommended follow-up, but don't auto-invoke it" design should use `AskUserQuestion` with a Yes/No choice from the first draft:

```json
{ "question": "Run enhancement-suggestor against these findings?", "header": "Next step",
  "options": [
    { "label": "Yes", "description": "Get a classified action plan" },
    { "label": "No", "description": "Skip for now" }
  ],
  "multiSelect": false }
```

**Rule of thumb:** if the next sentence after a finding or report is "you could..." or "consider running...", the design should be an `AskUserQuestion` gate. Reserve prose recommendations for cases where no concrete follow-up action exists.

### Mistake 6: Vague option descriptions

```json
// WRONG - the user can't tell what each option does
{ "options": [ { "label": "Option A", "description": "Yes" },
               { "label": "Option B", "description": "No" } ] }
```

**Fix:** write clear, actionable descriptions, such as "Build from scratch with proper structure" versus "Improve clarity, efficiency, or organization".

### Mistake 7: No escape hatch for genuine uncertainty

```json
// WRONG - forces a guess when the user may not know
{ "question": "Which of these categories fits this skill?",
  "options": [ {"label":"Category A"}, {"label":"Category B"}, {"label":"Category C"} ] }
```

**Fix:** add an "I'm not sure" option (Pattern 7) to any judgment-call question where a wrong guess would propagate downstream.

### Mistake 8: Listing "Other" yourself

The tool adds "Other" automatically. Spending one of your 4 option slots on it wastes the slot and shows the user two "Other" choices.

---

## Best Practices Checklist

When creating a skill that uses AskUserQuestion, verify:

- [ ] **2 to 4 options** per question, and **at most 4 questions** per call
- [ ] **Progressive disclosure:** ask one batch, wait, ask the next (no forms)
- [ ] **Clear descriptions:** the user understands what each option does
- [ ] **Free text through "Other":** no empty `options`, and no manual "Other" option
- [ ] **Conditional routing:** the next-question logic is clear (if/then paths documented)
- [ ] **Batching:** related independent questions grouped; dependent ones separated
- [ ] **Uncertainty option:** judgment-call questions include an "I'm not sure" path (Pattern 7)
- [ ] **Verified against the schema** (see below)

---

## Verification Patterns (For Skill Refinement)

When refining skills that use AskUserQuestion, check with the `Grep` tool, not shell commands:

1. Grep SKILL.md and `references/` for `options:` and inspect each AskUserQuestion definition. Expected: each shows 2-4 options, and none is `options: []`.
2. Grep for `questions:` and confirm no single call lists more than 4 questions.
3. When in doubt, compare against the limits stated in the tool's own definition.

**Rule:** if any question has more than 4 options, fewer than 2, or a call carries more than 4 questions, fix it before finishing.

---

## Token Impact

- **Single question with 2-4 options:** ~150-300 tokens
- **Multi-batch interview (3+ calls):** spread across interactions, efficient
- **Large form (10+ questions at once):** ~500+ tokens, worse UX, and rejected by the per-call cap

**Recommendation:** prefer progressive disclosure. Better UX, better token efficiency, more responsive feel.
