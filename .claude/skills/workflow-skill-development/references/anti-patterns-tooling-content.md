# Anti-Patterns Catalog — Tools, Content & Scalability

Tool, agent, content, scalability, and description anti-patterns (AP-11 through AP-20).

---

## Tool and Agent Anti-Patterns

### AP-11: Wrong Tool for the Job

**Symptom:** Skill uses `Bash` with `grep` instead of the `Grep` tool, or `Bash` with `find` instead of `Glob`.

**Why it's wrong:** Dedicated tools (Glob, Grep, Read) are optimized for their purpose, handle edge cases (permissions, encoding), and provide better output formatting. Bash equivalents are fragile and verbose.

**Before:**
```markdown
allowed-tools: Bash
```
```markdown
Find all Python files:
\`\`\`bash
find . -name "*.py" -type f
\`\`\`
```

**After:**
```markdown
allowed-tools: Glob Grep Read
```
```markdown
Find all Python files using Glob with pattern `**/*.py`.
```

---

### AP-12: Overprivileged Tool Lists

**Symptom:** Skill lists tools it never uses, or includes Write/Bash for a read-only analysis skill.

**Why it's wrong:** Extra tools expand the attack surface. A read-only analysis skill with Write access might create files the user didn't expect. Principle of least privilege applies.

**Before:**
```yaml
allowed-tools: Bash Read Write Glob Grep Task AskUserQuestion
```

**After (for a read-only analysis skill):**
```yaml
allowed-tools: Read Glob Grep
```

Only list tools the skill actually needs. Audit by checking which tools appear in instructions.

---

### AP-13: Vague Subagent Instructions

**Symptom:** Spawning a subagent with "analyze this code" and no specific instructions.

**Why it's wrong:** Subagents start fresh with no context. They need explicit instructions about what to look for, what format to produce, and what tools to use.

**Before:**
```markdown
Spawn a subagent to analyze the function.
```

**After:**
```markdown
Spawn a Task agent (subagent_type=Explore) with prompt:
"Read the function `processInput` in `src/handler.py`. List all external
calls it makes, what validation is performed on inputs, and whether any
input reaches a shell command or SQL query without sanitization.
Return findings as a markdown list."
```

---

### AP-14: Missing Tool Justification in Agents

**Symptom:** Agent frontmatter lists tools without the agent body explaining when to use each one.

**Why it's wrong:** Agents with ambiguous tool access make inconsistent choices about which tool to use for a given operation.

**Before:**
```yaml
tools: Read, Grep, Glob, Bash, Write
```
(Agent body never mentions when to use which tool.)

**After:**
```yaml
tools: Read, Grep, Glob
```
```markdown
## Tool Usage
- **Glob** to find files by pattern (e.g., `**/*.sol`, `**/SKILL.md`)
- **Read** to examine file contents after finding them
- **Grep** to search for specific patterns across files (e.g., `{baseDir}`, hardcoded paths)
```

---

## Content Anti-Patterns

### AP-15: Reference Dump Instead of Guidance

**Symptom:** Skill pastes a full specification or API reference instead of teaching when and how to use it.

**Why it's wrong:** The LLM already has general knowledge. What it needs is judgment: when to apply technique A vs B, what tradeoffs to consider, what mistakes to avoid.

**Before:** 200 lines of API documentation copied from official docs.

**After:**
```markdown
## When to Use X vs Y

Use X when:
- Input is structured and schema is known
- Performance matters (X is 10x faster)

Use Y when:
- Input format varies
- You need human-readable intermediate output

**Common mistake:** Using Y for structured input because it "feels safer."
Y's flexibility is overhead when the schema is known.
```

---

### AP-16: Missing Rationalizations Section

**Symptom:** Security/audit skill has no "Rationalizations to Reject" section.

**Why it's wrong:** LLMs naturally take shortcuts. Without explicit rationalization rejection, the LLM talks itself into skipping important steps. This is the #1 cause of missed findings in audit skills.

**Before:** Skill describes what to do but not what shortcuts to avoid.

**After:**
```markdown
## Rationalizations to Reject

| Rationalization | Why It's Wrong |
|-----------------|----------------|
| "The code looks clean, skip deep analysis" | Surface appearance doesn't indicate security. Analyze every entry point. |
| "This is a well-known library, it's safe" | Libraries have bugs. Check the specific version and usage pattern. |
| "No findings means the code is secure" | Zero findings may indicate poor analysis, not good code. |
```

---

### AP-17: No Concrete Examples

**Symptom:** Skill describes rules in abstract terms without showing input -> output.

**Why it's wrong:** Abstract rules are ambiguous. Concrete examples anchor the LLM's understanding and reduce interpretation drift.

**Before:**
```markdown
Ensure the output is well-formatted and includes all relevant information.
```

**After:**
```markdown
## Output Format

\`\`\`markdown
## Analysis Report

### Findings
| # | File | Line | Issue | Severity |
|---|------|------|-------|----------|
| 1 | src/auth.py | 42 | SQL injection via unsanitized user input | High |

### Summary
- 3 findings total (1 high, 2 medium)
- Primary risk area: input validation in authentication module
\`\`\`
```

---

## Scalability Anti-Patterns

### AP-18: Cartesian Product Tool Calls

**Symptom:** Skill says "find all matching files, then search each file for each pattern" — producing N files × M patterns = N×M tool calls.

**Why it's wrong:** The agent won't actually execute N×M calls. It will shortcut — scanning a few files, skipping patterns, or summarizing early — and miss results silently. Even if it tries, the volume of calls degrades response quality and exhausts context.

**Before:**
```markdown
### Phase 2: Search for Vulnerabilities
1. Use Glob to find all `.sol` files
2. Filter out test paths
3. For each file, Grep for each of these 12 patterns:
   - `delegatecall`
   - `selfdestruct`
   - `tx.origin`
   - `block.timestamp`
   - ... (8 more patterns)
```

**After:**
```markdown
### Phase 2: Search for Vulnerabilities
1. Grep the codebase for `delegatecall|selfdestruct|tx\.origin|block\.timestamp|...` (single combined regex)
2. Filter results to exclude test paths (`**/test/**`, `**/mock/**`)
3. Read matching files for context around each hit
```

Combine patterns into one regex. Grep once across the codebase. Filter results afterward.

---

### AP-19: Unbounded Subagent Spawning

**Symptom:** Skill says "spawn one subagent per file" or "one subagent per function" — subagent count scales with codebase size.

**Why it's wrong:** With 1000 files, that's 1000 subagents. The agent will hit context limits, refuse, or produce degraded results long before finishing. Even with 50 files, spawning 50 subagents creates massive overhead and unpredictable execution.

**Before:**
```markdown
### Phase 3: Analyze Code
For each code file discovered in Phase 2, spawn a Task subagent to:
- Read the file
- Build a summary of its public API
- Identify potential issues
```

**After:**
```markdown
### Phase 3: Analyze Code
Batch discovered files into groups of 10-20. For each batch, spawn a single Task subagent with prompt:
"Read the following files: [list]. For each file, summarize its public API and identify potential issues. Return a markdown table with one row per file."
```

Batch items into fixed-size groups. One subagent per batch, not one per item.

---

## Description Anti-Patterns

### AP-20: Description Summarizes Workflow

**Symptom:** The `description` field summarizes the skill's workflow steps instead of listing triggering conditions.

**Why it's wrong:** Claude treats the description as an executive summary. When it contains workflow steps ("dispatches subagent per task with code review between tasks"), Claude follows the description and shortcuts past the actual SKILL.md body. A description saying "code review between tasks" caused Claude to do ONE review, even though the SKILL.md flowchart showed TWO reviews (spec compliance then code quality). When the description was changed to triggering conditions only, Claude correctly read and followed the full process.

**Before:**
```markdown
---
name: subagent-driven-development
description: >-
  Use when executing plans — dispatches subagent per task
  with code review between tasks for quality assurance
---
```

**After:**
```markdown
---
name: subagent-driven-development
description: >-
  Use when executing implementation plans with independent
  tasks in the current session
---
```

The description should contain ONLY triggering conditions ("Use when..."), never workflow steps. Process details belong in the SKILL.md body.
