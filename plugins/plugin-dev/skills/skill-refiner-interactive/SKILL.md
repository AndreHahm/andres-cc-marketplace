---
name: skill-refiner-interactive
description: >-
  Improves, validates, and optimizes existing Claude Code skills for clarity, efficiency, and
  production readiness. Use when refining skills, improving skill structure, validating against
  best practices, reducing token usage, consolidating references, checking production readiness,
  applying the 80% rule, or running interactive fix-review workflows on existing skills.
  Not for creating new skills — use skill-development instead. For a one-shot structured
  quality report with no interactive back-and-forth, use the skill-reviewer agent instead —
  this skill wraps skill-reviewer in Validation mode and then interactively applies fixes.
  For fully automated, non-interactive fix-review loops with no user checkpoints, use
  skill-improver-loop instead.
allowed-tools: Read Edit Write Glob Grep Skill Agent
---

# Interactive Skill Refiner

Systematically improve and validate Claude Code skills while preserving functionality and following established patterns.

## Quick Start

**Step 0: Detect Predating Context (Escape Hatch)**

Check conversation history for predating context:
- Skill file or code already provided?
- Problem or issue already described?
- Skill actively being discussed?

**IF PREDATING CONTEXT EXISTS** → Offer escape hatch immediately:

```
questions: [
  {
    question: "I've reviewed the skill and context you provided. How would you like to proceed?",
    header: "Interview Style",
    options: [
      {
        label: "Infer from context",
        description: "I'll infer refinement needs from what you shared. Skip detailed interview (faster)"
      },
      {
        label: "Define explicitly",
        description: "I'll ask you to explicitly define improvement areas and goals (full interview)"
      }
    ],
    multiSelect: false
  }
]
```

Then route:
- **"Infer from context"** → Skip to BATCH 2 with context-tailored prompts
- **"Define explicitly"** → Full BATCH 1 + BATCH 2

**IF NO PREDATING CONTEXT** → Continue to Step 1

**Step 1:** Use AskUserQuestion to ask: **"What skill do you want to work on?"** (open-form text input)

**Step 2:** Use AskUserQuestion with **predefined options** to ask:

```
questions: [
  {
    question: "What would you like to do with this skill?",
    header: "Action",
    options: [
      {
        label: "Refine",
        description: "Improve clarity, structure, efficiency, token usage, or organization"
      },
      {
        label: "Validate",
        description: "Check if it's production-ready (tool scoping, completeness, error handling, trigger phrases)"
      }
    ],
    multiSelect: false
  }
]
```

**Step 3:** Route based on their selection:

- **If "Refine"** → Proceed to **Core Workflow: Refinement** (BATCH 1 + BATCH 2 interview questions follow during the workflow)
- **If "Validate"** → Skip interview, go directly to **Core Workflow: Validation**

## Core Workflow: Refinement

**When user requests refinement:**

1. **Locate the skill (MANDATORY first step)**
   - Search current project first: `skills/skill-name/`, `.claude/skills/skill-name/` — exclude gitignored paths per `plugin-rulebook/references/gitignore-exclusion.md` (Glob `**/plugin-rulebook/SKILL.md` to find it, if present); a matching draft in a gitignored directory like `to-implement/`, `.planned/`, or `.backup/` is not the real target
   - **Mirror-pair check (R19):** if both `skills/skill-name/` and `.claude/skills/skill-name/` exist under the same plugin, this is an in-development staging mirror, not two independent skills. Diff `SKILL.md` and every `references/`/`scripts/` file between the two copies:
     - Identical → treat as one logical skill; every edit made during this workflow applies to BOTH copies; re-verify byte-identical before finalizing
     - Differ → HALT per R19 and ask which copy is authoritative before proceeding:
       ```
       {
         question: "Found this skill at both `[path A]` and `[path B]`, but their content differs — this looks like a broken in-development mirror pair (R19), not two independent skills. Which is authoritative?",
         header: "Mirror Divergence",
         options: [
           { label: "Show me the diff first", description: "Display what differs between the two copies before deciding" },
           { label: "[path A] is correct", description: "Overwrite [path B] with [path A]'s content, then proceed with refinement" },
           { label: "[path B] is correct", description: "Overwrite [path A] with [path B]'s content, then proceed with refinement" },
           { label: "Stop — I'll resolve it myself", description: "Don't touch either copy; end this session so the operator can reconcile manually" }
         ]
       }
       ```
   - If not found in project → Check user-space: `~/.claude/skills/skill-name/`
   - If found in user-space → WARN: "This affects all projects. Continue?"
   - If in cache (`~/.claude/plugins/cache/`) → REFUSE: "That's an installed copy (read-only)"
   - If not found anywhere → ASK: "Where should I find this skill?"

   **Immediately after locating — pre-analyze before any interview:**
   - Check for `plugin-rulebook` skill (Glob `**/plugin-rulebook/SKILL.md`); if found, read its `assets/settings.json` and load BOTH R13 (SKILL.md line-count) and R18 (inline code-block size) tiered thresholds — these supersede the flat limits below for the rest of pre-analysis. If not found, fall back to `skill-development/references/size-limits.md`'s flat 500-line / 10-line limits.
   - Read SKILL.md; count body lines (exclude frontmatter); classify against the resolved R13 tiers (OK / Weak Warning / Soft Warning / Warning / Critical) — don't treat 500 as the only threshold worth reporting; a Soft Warning at, say, 350 lines is worth surfacing even though it's non-blocking
   - Scan frontmatter: flag `AskUserQuestion` in `allowed-tools`, non-standard fields (`version:`), single-line `description` (needs `>-`) — `allowed-tools` may be space-separated, comma-separated, or a YAML list (space-separated is preferred style, not a requirement), and `argument-hint` is an allowed skill field, not a violation
   - Identify sections ≥50 lines; classify core (80%+ usage) vs. low-frequency (<20%)
   - List reference files; note topically related clusters (≥2 files, same domain); flag any `references/*.md` ≥400 lines
   - Check all `workflows/*.md`; flag any ≥300 lines; scan each for links to `references/` files used as action steps (workflow→reference chain violation); also scan each `references/*.md` for imperative directives to read another `references/` file (reference→reference chain violation)
   - Scan SKILL.md and all `references/*.md` for spawn anti-patterns: Cartesian product spawning (subagents spawned for every combination of two or more independent lists), unbounded agent spawning (spawn inside a loop with no explicit count cap where the list is user-controlled), vague subagent prompts (dispatch instructions with no file paths, no goal statement, no output spec)
   - Scan SKILL.md for sections that handle user intake: grep for `ask the user`, `prompt the user`, free-form `questions:` blocks (i.e., `questions:` key present but no `options:` key in the same block). Flag each as a behavioral intake violation — sections that collect input without `AskUserQuestion` should be converted to use it
   - Check R22 argument-hint/arguments consistency: if `plugin-rulebook` was found above, read its `references/argument-consistency.md` for the detection procedure; otherwise scan the body directly for `$ARGUMENTS`, `$ARGUMENTS[N]`, a bare unescaped `$0`/`$1`/`$2`/..., or `$name` for a name declared in `arguments`. Compare against frontmatter `argument-hint`/`arguments`: flag a missing declaration (body accepts arguments but frontmatter is empty), an orphaned declaration (frontmatter declares a slot never referenced in the body), or a wrong-position mismatch (declared order doesn't match consumption order). Catching this in pre-analysis lets the operator fix it as part of BATCH 2 instead of only via the mandatory `plugin-rulebook` gate at the end of the workflow.
   - Check for a `when_to_use`-split candidate: if no `when_to_use` field is present, scan `description` for an embedded trigger-condition clause (e.g., a `Use when` / `use when` phrase mid-description). If found and `description` alone exceeds roughly 400 characters, flag it — the trigger conditions could move to `when_to_use`, tightening `description` to the "what" per `skill-development`'s What+When formula (see `skill-development/references/content-guidelines.md`).

   **Emit pre-analysis report before proceeding:**
   ```
   📋 Pre-Analysis: <skill-name>
   Lines: X — [OK | Weak Warning | Soft Warning | Warning | Critical] (R13)
   Frontmatter issues: [list or "none"]
   Large sections (≥50 lines): [name — X lines | "none"]
   Reference files: N [clusters: list | "none"] [oversize ≥400 lines: list | "none"]
   Workflow files: N [oversize ≥300 lines: list | "none"] [workflow→ref chain violations: list | "none"]
   Reference chain violations (ref→ref): [list | "none"]
   Spawn anti-patterns: [list | "none"]
   Intake pattern violations: [section name — reason | "none"]
   Argument consistency (R22): [mismatch description | "none"]
   when_to_use split candidate: [description length + embedded trigger clause | "no"]
   R13/R18 threshold source: [plugin-rulebook/assets/settings.json | skill-development fallback]
   ```

### Requirements Interview (Progressive Disclosure - One Batch at a Time)

After locating and pre-analyzing the skill, **interview to gather what they want improved** using AskUserQuestion with proper options.

**🔴 BATCH 1: Refinement Focus** (Progressive AskUserQuestion - ask one at a time):

#### Question 1: What aspects need improvement?

```
questions: [
  {
    question: "What aspects need improvement?",
    header: "Focus Areas",
    options: [
      { label: "Clarity", description: "Make instructions clearer, remove jargon, improve examples" },
      { label: "Efficiency", description: "Reduce token usage, consolidate references, optimize content" },
      { label: "Structure", description: "Reorganize sections, improve flow, better grouping" },
      { label: "User Interaction UX", description: "Convert free-form interactions to AskUserQuestion patterns, improve workflows" }
    ],
    multiSelect: true
  }
]
```

#### Question 2: What specific problems are you seeing?

```
questions: [
  {
    question: "What specific problems are you seeing?",
    header: "Key Issues"
  }
]
```

(Examples: "Instructions are hard to follow", "References scattered and redundant", "Too many nested sections")

#### Question 3: What would success look like?

```
questions: [
  {
    question: "What would success look like?",
    header: "Success Metric"
  }
]
```

(Examples: "Clearer workflow", "Fewer token costs", "Production-ready with error handling")

#### Question 4: Any areas to exclude or preserve as-is?

```
questions: [
  {
    question: "Any areas to exclude or preserve as-is?",
    header: "Scope Limits"
  }
]
```

(Examples: "Keep the validation gates", "Don't change tool scoping")

After gathering ALL responses, document approved scope and proceed to BATCH 2.

**🟢 BATCH 2: Implementation Details**

**ROUTING NOTE:**
- If user chose **"Infer from context"** in escape hatch → Skip BATCH 1, come straight here
- If user chose **"Define explicitly"** → Proceed after BATCH 1 responses
- **Questions are conditional on pre-analysis findings** — ask only questions relevant to what was detected

**If no issues detected by pre-analysis:** Skip BATCH 2, proceed directly to step 3.

**For each large low-frequency section detected (≥50 lines, estimated <20% usage):**
```
{
  question: "Section '[NAME]' is X lines and appears in <20% of activations. Extract to `references/[name].md`?",
  header: "Content Extraction",
  options: [
    { label: "Yes", description: "CREATE reference file, LINK in SKILL.md, DELETE inline" },
    { label: "No", description: "Keep inline" }
  ]
}
```

**For each intake pattern violation detected (section collects input without AskUserQuestion):**
```
{
  question: "Section '[NAME]' collects user input without AskUserQuestion ([reason]). Convert to structured AskUserQuestion with options?",
  header: "Intake Pattern",
  options: [
    { label: "Yes", description: "Replace free-form intake with AskUserQuestion block; define options from observed inputs" },
    { label: "No", description: "Keep free-form — this section intentionally uses open-ended input" }
  ]
}
```

**For related reference file clusters detected (≥2 files on same topic):**
```
{
  question: "Found related reference files: [list]. Consolidate into one file?",
  header: "Consolidation",
  options: [
    { label: "Yes", description: "Merge related files for clarity, update SKILL.md pointers" },
    { label: "No", description: "Keep current structure" }
  ]
}
```

**For an R22 argument-hint/arguments mismatch detected in pre-analysis:**
```
{
  question: "Frontmatter argument-hint/arguments doesn't match what the body actually consumes ([mismatch description]). Fix now?",
  header: "Argument Consistency",
  options: [
    { label: "Yes", description: "Update argument-hint/arguments to match body usage (add missing slot / remove orphaned slot / fix ordering)" },
    { label: "No", description: "Leave as-is — the end-of-workflow plugin-rulebook gate will still catch it" }
  ]
}
```

**For a `when_to_use`-split candidate detected in pre-analysis:**
```
{
  question: "description is X characters and embeds trigger conditions inline (no when_to_use field present). Split into description (what) + when_to_use (when)?",
  header: "Description Split",
  options: [
    { label: "Yes", description: "Extract the trigger-condition clause into a new when_to_use field; keep description focused on what+scope" },
    { label: "No", description: "Keep as a single description field" }
  ]
}
```

**For production hardening (ask in every refinement session):**
```
{
  question: "Which production checks should I run?",
  header: "Production Checks",
  options: [
    { label: "Security scan", description: "Grep for hardcoded credentials, API keys, or tokens in SKILL.md and scripts/; also audit substitution variables (grep `\\$\\{[A-Z_]+\\}` in SKILL.md) — these silently corrupt example code in documentation context" },
    { label: "Error handling", description: "Verify skill handles missing files, malformed YAML, and permission errors" },
    { label: "Tool scoping", description: "Audit allowed-tools: remove unused tools, narrow Bash wildcards to specific commands" },
    { label: "None needed", description: "Skip production checks for this session" }
  ],
  multiSelect: true
}
```

Note: Standard sections (Quick Start, When to Use/NOT, Testing & Validation, Reference Guide) are auto-added in step 5 — no question needed.

After gathering responses (if any), document approved scope and proceed.

---

2. **Load workflow reference**
   - Review `references/refinement-workflow.md` for the complete refinement workflow with all preservation gates and validation phases

3. **Identify consolidation opportunities (BEFORE changes)**
   - List all files in `references/` directory with line counts
   - Group by topic (what do they cover?)
   - Flag potential merges (2-4 files on same topic → 1 consolidated file)
   - ASK: "Should we consolidate these files? Saves N lines, improves clarity"
   - Only proceed if operator approves

4. **Apply preservation gates (CRITICAL - four gates, in order)**
   - **GATE 1**: Content Audit - list ALL existing content, classify as core (80%+) or supplementary (<20%)
   - **GATE 2**: Capability Assessment - will changes impair execution? If YES → cannot delete, only migrate
   - **GATE 3**: Migration Verification - before moving content, verify destination exists and is complete
   - **GATE 4**: Operator Confirmation - deletions require explicit approval, migrations auto-approved

5. **Make changes (following movement pattern)**
   - CREATE/UPDATE destination FIRST (new file, updated section)
   - LINK - update SKILL.md pointers to new destination
   - DELETE old source (only after links verified)
   - Never delete first; always: CREATE → LINK → DELETE
   - **Standard sections — auto-add when absent (no operator approval needed):**
     - `## Quick Start` — actionable first steps (not theory)
     - `## When to Use` — concrete trigger conditions (bullet list)
     - `## When NOT to Use` — explicit redirections with named alternatives
     - `## Testing & Validation` — 3-5 checks + quality gates checklist
     - `## Reference Guide` — table of all `references/` files with purpose column

6. **Validate result (seven phases)**
   - Phase 1: File Inventory - list structure before/after
   - Phase 2: Read All - load complete content, verify no gaps
   - Phase 3: Frontmatter - check required metadata (name, description)
   - Phase 4: Body Content - re-check against the resolved R13 tiers from pre-analysis (not just <500), 80% rule applied, clarity improved; check workflow pattern (load `design-patterns.md`) and spawn anti-patterns
   - Phase 5: References - confirm all linked files exist, complete, one level deep, no reference→reference chains
   - Phase 6: Tools - three-step reconciliation: undeclared tools, unused declared tools, Bash-for-dedicated-tool misuse
   - Phase 7: Testing - verify activation with real-world trigger phrases

7. **If `description` or `when_to_use` changed, check for trigger regression before finalizing**
   ```
   {
     question: "The description changed. Verify trigger accuracy didn't regress before finalizing?",
     header: "Trigger Regression Check",
     options: [
       { label: "Run trigger-eval check", description: "Delegate to Skill(skill-development) to run its Phase 5 description-optimization loop (run_loop.py) against an eval set, comparing old vs. new description trigger accuracy" },
       { label: "Quick size check only", description: "Skip the eval loop; just diff the new description/when_to_use against plugin-rulebook's R21 length tiers (or skill-development's size-limits.md fallback) to catch bloat or under-length regressions" },
       { label: "Skip", description: "Finalize without a regression check — acceptable for minor wording tweaks that don't touch trigger phrases" }
     ]
   }
   ```
   - **"Run trigger-eval check"**: this skill has no `Bash` access and does not run `run_loop.py` itself — invoke `Skill(skill-development)` and ask it to run Phase 5's description-optimization loop against this skill. If no eval set exists yet, a small ad hoc set (3-6 should-trigger / should-not-trigger queries covering the changed trigger phrases) is enough for a refinement pass — the full 20-query set is `skill-development`'s own greenfield-polish standard, not required here. Report the before/after trigger accuracy it returns.
   - **"Quick size check only"**: report the new `description`/`when_to_use`/combined lengths against R21's tiers; flag if the change crossed into a worse tier than before.
   - Skip this step entirely if neither field changed during this refinement session.

8. **Run compliance and reviewer passes, then emit completion marker**
   - Call `Skill(plugin-rulebook)` for a full compliance check (all enabled rules, not just R13/R18) on the updated skill — this is a standing project requirement (`.claude/rules/plugin-rulebook-enforcement.md`) for any operation that modifies a skill. If the located skill is an R19 mirror pair, run this against both copies after they're re-verified identical.
   - Fix all FAIL (REQUIRED-rule) findings from that report; a FAIL blocks completion the same as a Critical `skill-reviewer` finding
   - Call `skill-reviewer` on the updated skill
   - Fix all Critical and Major issues found; repeat until no C/M issues and no plugin-rulebook FAIL findings remain
   - Emit change summary:
   ```
   Lines: X → Y
   Frontmatter: [fixes applied, or "no changes"]
   Sections added: [list, or "none"]
   Files created: [list, or "none"]
   Files deleted: [list, or "none"]
   plugin-rulebook: [PASS | N FAIL findings fixed]
   ```
   Only emit `<skill-improvement-complete>` after `plugin-rulebook` reports no FAIL findings AND `skill-reviewer` confirms no Critical or Major issues remain:
   ```
   <skill-improvement-complete>
   ```

## Core Workflow: Validation

**When user requests validation:**

1. **Locate the skill** (same as refinement step 1 — includes the gitignore-exclusion and R19 mirror-pair checks; if the skill is a mirror pair, everything below runs once against the synced content, not once per copy)

2. **Delegate to `skill-reviewer` and `plugin-rulebook`** — do not reimplement their checks here; this skill's job is routing and presentation, not a second, independently-drifting scoring system
   - Call `skill-reviewer` (full mode, **Structured output mode**) on the located skill. It owns: file inventory, frontmatter validation, the R13/R18 gatekeeper checks (via its own `plugin-rulebook` lookup), the 100-pt Activation/Implementation rubric, the checklist pass (references, tool reconciliation, chain-violation detection, spawn anti-patterns, workflow pattern validation), and the Critical/Major/Minor severity findings — returned as YAML (`verdict`, `score`, `counts`, `findings[]`, `top_priority_fixes`) per its own Structured Output Mode schema, not the narrative report. Requesting structured output here makes the branching in step 3 a direct field read instead of prose-parsing, while this skill still renders a human-readable summary from it.
   - Call `Skill(plugin-rulebook)` separately for a full compliance check (all enabled rules, not just the R13/R18 subset `skill-reviewer` loads) — a standing project requirement (`.claude/rules/plugin-rulebook-enforcement.md`) for any component being validated. This is the only check that covers R4, R19, R21, R22, R23, and the rest of the rule set `skill-reviewer` doesn't touch.

3. **Present the report**
   - Render `skill-reviewer`'s YAML into a narrative summary for the user: `verdict` as the headline status (S-Tier / Pass / Reject, unchanged from the scale `skill-reviewer` defines), `findings[]` grouped by `severity` the same way the narrative report would present them, `top_priority_fixes` as the actionable list
   - Append any `plugin-rulebook` FAIL findings under their own heading; a FAIL downgrades an otherwise-Pass `verdict` to Reject in the summary shown to the user (this downgrade is this skill's own presentation logic — it does not change what `skill-reviewer` itself returned)
   - Surface `top_priority_fixes` and any plugin-rulebook FAILs together as the actionable summary
   - If `verdict` is Reject (after the plugin-rulebook downgrade above), or `counts.critical` or `counts.major` is nonzero, ask with `AskUserQuestion`: "Run `enhancement-suggestor` against this report for a classified (complexity/risk/benefit) WHAT/WHY/HOW action plan?" — options "Yes" / "No". If yes, invoke the `enhancement-suggestor` agent (via `Agent`) against the combined report. Never invoke it without asking first

## Automated Improvement Loop

For automated fix-review cycles — iterating a skill until it passes `skill-reviewer` with no Critical/Major issues, without manual editing each round — use the dedicated `skill-improver-loop` skill instead of repeating that workflow here. It owns issue categorization, the completion marker, and the stop-hook contract; this skill is for interactive, operator-guided refinement and validation.

## Evidence-Gated Editing (Optional Rigor)

Apply when optimizing a skill with observed failures or measured drift. An edit ships only when it demonstrably beats the version already in use.

Score the current and proposed versions on a fixed held-out check set (3–8 tasks, including the triggering failure). Accept only if the candidate strictly beats the current on the triggering criterion with no regression on others. Cap at ~4 changes per revision; rank by systematic impact.

## Key Rules (Non-Negotiable)

### The 80% Rule (Content Distribution)
- Will Claude execute this in 80%+ of skill activations? → **STAYS in SKILL.md**
- Will Claude execute this in <20% of cases? → **CAN MOVE to references/**
- Uncertain? → **DEFER to operator; keep in SKILL.md by default**

### Movement Pattern (for content changes)
```
SEQUENCE (never violate order):
1. CREATE/UPDATE destination file(s) with merged content
2. LINK - Update SKILL.md pointers to new destination(s)
3. DELETE old source (only after links verified and tested)

NEVER: DELETE → LINK → CREATE (creates broken links and lost content)
```

**Visual flow:**

```
    ❌ WRONG                              ✅ CORRECT

    DELETE old source                     CREATE destination
            │                                     │
            ▼                                     ▼
    LINK to new location                  LINK pointers
            │                                     │
            ▼                                     ▼
    CREATE destination                    DELETE old source
    (broken links!)                       (safe, links verified)
```

### Preservation Gates (Four Gates, In Order)
1. **Content Audit** - List ALL existing content. Classify using **the 80% rule**: core content (used in 80%+ of activations) vs. supplementary (<20%). See `references/80-percent-rule.md` for full decision framework.
2. **Capability Assessment** - Will changes impair execution? If YES → cannot delete, only migrate
3. **Migration Verification** - Before moving, verify destination complete. NO GAPS
4. **Operator Confirmation** - Deletions require explicit approval. Migrations auto-approved

### Scope Rules (Where to Work)
✅ **PREFERRED** - Project paths (search first):
- `skills/skill-name/` in plugin projects
- `.claude/skills/skill-name/` in any project

⚠️ **CONDITIONAL** - User-space (only if not in project):
- `~/.claude/skills/skill-name/` - WARN: "Affects all projects"
- Requires explicit user confirmation before editing
- Offer to copy to project instead

❌ **FORBIDDEN** - Never edit (REFUSE IMMEDIATELY):
- `~/.claude/plugins/cache/*` (installed plugins - read-only)
- Any path containing `/cache/` (always read-only)

## Reference Guide

### Refining for Clarity
Remove jargon, improve examples, restructure for flow
→ `references/ask-user-question-patterns.md` for interaction patterns
→ `references/content-guidelines.md` for description improvement

### Refining for Efficiency (Token Usage)
Apply 80% rule, consolidate references, optimize content
→ `references/80-percent-rule.md` for content distribution decisions
→ `references/movement-pattern.md` for safe migration procedure

### Refining for Structure
Reorganize sections, improve grouping, better information flow
→ `references/refinement-workflow.md` for unified workflow with gates
→ `references/movement-pattern.md` for safe content relocation
→ `references/advanced-patterns.md` for archetype structures

### Preserving Functionality (Safety Gates)
Never break existing behavior, never delete without knowing where content goes
→ `references/preservation-rules.md` for what NEVER gets cut
→ `references/refinement-guardrails.md` for safe patterns
→ `references/movement-pattern.md` for CREATE → LINK → DELETE sequence

### Validating Quality
Check production readiness, tool scoping, completeness
→ `references/validation-checklist.md` for comprehensive assessment
→ `references/production-patterns.md` for error handling and team patterns
→ `references/allowed-tools.md` for tool scoping validation

### Optimizing Against Evidence
Evidence-gated revision
→ `references/refinement-workflow.md` for complete workflow

### Plugin Rules
Plugin-level naming, language, formatting, and tool-scoping compliance
→ Invoke `plugin-rulebook` skill for active rule configuration and compliance check


## Gotchas

- **Deleting before creating the destination.** Always follow CREATE → LINK → DELETE order. Reversing it breaks links and loses content before the destination exists.
- **Moving core content to references/ to reduce line count.** Never move content used in 80%+ of activations just to shrink the file — it impairs execution. Apply the 80% rule, not a line-count rule.
- **Editing skills in `~/.claude/plugins/cache/`.** These are read-only installed copies. REFUSE immediately and guide the user to the correct editable path.
- **Temporary orphan warnings during CREATE → LINK → DELETE.** The validate-frontmatter hook fires "orphaned file" warnings after the CREATE step, before LINK references the new file. This is an expected interim state — warnings resolve after the LINK step. Only investigate if warnings persist after all edits are complete.
- **Context compacted after BATCH 2 but before edits applied.** If the session is summarized mid-refinement, the operator's BATCH 2 approvals are in the summary. Re-read the target SKILL.md, reconstruct the plan from the summary, and apply edits without re-interviewing.

## Common Scenarios

See `references/common-scenarios.md` for step-by-step guidance on: simplifying a skill, reducing token usage, improving UX interactions, improving reference quality, production-readiness checks, underperforming skill optimization, and running the improvement loop.
