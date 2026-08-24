# Anti-Patterns Catalog — Structure & Workflow Design

Common mistakes in workflow-based skill structure and workflow design (AP-1 through AP-10).

---

## Structure Anti-Patterns

### AP-1: Vague Description and Missing Scope Sections

**Symptom:** Skill has a vague `description` in frontmatter and no "When to Use" or "When NOT to Use" sections in the body.

**Why it's wrong:** Claude decides whether to activate a skill based solely on the `description` field. A vague description causes wrong activations or missed activations. Once active, "When to Use" and "When NOT to Use" sections scope the LLM's behavior — without them, the LLM attempts tasks outside the skill's competence.

**Before:**
```markdown
---
name: analyzing-logs
description: "Analyzes log files"
---
# Log Analysis
Here's how to analyze logs...
```

**After:**
```markdown
---
name: analyzing-logs
description: >-
  Analyzes structured log files (JSON, logfmt) for error triage,
  cross-service event correlation, and recurring pattern detection.
  Use when triaging application errors or investigating incidents.
  NOT for real-time monitoring, binary files, or metrics/tracing.
---

## When to Use
- Triaging application errors from structured log files (JSON, logfmt)
- Correlating log events across multiple services
- Identifying recurring error patterns over time

## When NOT to Use
- Real-time log monitoring — use dedicated observability tools
- Binary file analysis — this skill handles text-based logs only
- Metrics or tracing analysis — use APM-specific skills
```

The `description` controls activation. The body sections scope behavior after activation.

**Format rule:** Start descriptions with triggering conditions ("Use when..."), use third-person voice ("Analyzes X" not "I analyze X"), and include specific trigger keywords. See also AP-20 for the related trap of putting workflow steps in the description.

---

### AP-2: Monolithic SKILL.md

**Symptom:** SKILL.md exceeds 500 lines with everything inlined.

**Why it's wrong:** see `progressive-disclosure-guide.md`'s "The 500-Line Rule" for the full rationale (LLM attention degradation) — not restated here.

**Before:** A 900-line SKILL.md with full API documentation, examples, and workflow steps all in one file.

**After:** SKILL.md under 500 lines with core principles and routing. Detailed reference material in `references/`. Step-by-step processes in `workflows/`. SKILL.md links to these with one-line summaries.

---

### AP-3: Reference Chains

**Symptom:** SKILL.md links to file A, which links to file B, which links to file C.

**Why it's wrong:** see `progressive-disclosure-guide.md`'s "The One-Level-Deep Rule" for the full rationale — not restated here.

**Before:**
```
SKILL.md -> references/setup.md -> references/advanced-setup.md -> references/edge-cases.md
```

**After:**
```
SKILL.md -> references/setup.md (includes advanced and edge cases)
SKILL.md -> references/edge-cases.md (standalone)
```

All files are one hop from SKILL.md. Files do not reference other reference files.

---

### AP-4: Hardcoded Paths

**Symptom:** File contains absolute paths like `/Users/jane/projects/skill/scripts/run.py`.

**Why it's wrong:** The skill breaks for any user whose filesystem differs. This is always wrong, with no exceptions.

**Before:**
```markdown
Run the script:
\`\`\`bash
python /Users/jane/projects/my-skill/scripts/analyze.py
\`\`\`
```

**After:**
```markdown
Run the script:
\`\`\`bash
uv run {baseDir}/scripts/analyze.py
\`\`\`
```

---

### AP-5: Missing File References Validation

**Symptom:** SKILL.md references `workflows/advanced.md` but the file doesn't exist.

**Why it's wrong:** The LLM attempts to read the file, fails, and either hallucinates the content or stops. Broken references are silent failures that produce unpredictable behavior.

**Fix:** Before submitting, verify every path referenced in SKILL.md exists. Use glob to check.

---

## Workflow Design Anti-Patterns

### AP-6: Unnumbered Phases

**Symptom:** Workflow uses prose paragraphs or vague headings instead of numbered phases.

**Why it's wrong:** The LLM cannot reliably determine ordering from prose. Numbered phases with entry/exit criteria create unambiguous execution order.

**Before:**
```markdown
## Workflow
First, gather the data. Then analyze it. After that, present findings.
Make sure to validate before presenting.
```

**After:**
```markdown
## Workflow

### Phase 1: Gather Data
**Entry:** User has specified target directory
**Actions:**
1. Scan directory for relevant files
2. Validate file formats
**Exit:** File list confirmed, all formats valid

### Phase 2: Analyze
**Entry:** Phase 1 complete
**Actions:**
1. Run analysis on each file
2. Aggregate results
**Exit:** Analysis results stored in structured format

### Phase 3: Present Findings
**Entry:** Phase 2 complete
**Actions:**
1. Validate results against expected schema
2. Format and present to user
**Exit:** User has received formatted report
```

---

### AP-7: Missing Exit Criteria

**Symptom:** Phases say what to do but not how to know when it's done.

**Why it's wrong:** Without exit criteria, the LLM may produce incomplete work for a phase and move on, or loop endlessly trying to "finish" a phase with no definition of done.

**Before:**
```markdown
### Phase 2: Build Database
Build the CodeQL database from the source code.
```

**After:**
```markdown
### Phase 2: Build Database
**Entry:** Language detected, build command identified
**Actions:**
1. Run `codeql database create` with detected settings
2. Verify database creation succeeded
**Exit:** Database exists, `codeql resolve database` returns success, extracted file count > 0
```

---

### AP-8: No Verification Step

**Symptom:** The workflow ends with "output the results" and no validation.

**Why it's wrong:** LLMs can produce plausible but incorrect output. A verification step catches errors before the user acts on bad results.

**Before:**
```markdown
### Phase 3: Generate Report
Write the analysis report to output.md.
```

**After:**
```markdown
### Phase 3: Generate Report
1. Write analysis report to output.md
2. Verify: all input files are represented in the report
3. Verify: no placeholder text remains
4. Verify: all referenced paths exist

Report to user:
- Key findings (2-3 bullet points)
- Any warnings or limitations
```

---

### AP-9: Vague Routing Keywords

**Symptom:** Multiple workflows match the same user input because routing keywords overlap.

**Why it's wrong:** Ambiguous routing causes the LLM to pick the wrong workflow or freeze deciding between them.

**Before:**
```markdown
| "analyze" | `workflows/static-analysis.md` |
| "analyze code" | `workflows/dynamic-analysis.md` |
```

**After:**
```markdown
| "static", "scan", "lint", "find bugs" | `workflows/static-analysis.md` |
| "dynamic", "fuzz", "runtime", "execute" | `workflows/dynamic-analysis.md` |
```

Use distinctive keywords per workflow. If two workflows genuinely overlap, add a disambiguation step.

---

### AP-10: No Default/Fallback Route

**Symptom:** Routing table covers known options but has no catch-all.

**Why it's wrong:** When user input doesn't match any route, the LLM improvises. The improvised behavior is unpredictable and usually wrong.

**Before:** Routing table with 5 specific options and nothing else.

**After:**
```markdown
| None of the above | Use `AskUserQuestion` — question: "Which would you like?", options: "X" / "Y" / "Z" |
```
