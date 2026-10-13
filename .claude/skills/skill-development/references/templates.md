# Templates for Skill Creation

## Content-Size Decision Tree

For the authoritative decision tree (which specific content goes in SKILL.md vs. references/, including the ~100-line content-type-specific trigger for API docs/schema tables/background material), see `skill-workflow.md` Part 1 (the 80% Rule) — not restated here to avoid drift with a conflicting flat threshold.

## Table of Contents
- [SKILL.md Template](#skillmd-template)
- [Reference File Template](#reference-file-template)
- [Description Formula & Examples](#description-formula--examples)
- [Workflow Pattern Examples](#workflow-pattern-examples)
- [Optional Frontmatter Fields](#optional-frontmatter-fields)
- [Structure Validation](#structure-validation)
- [Token Efficiency Tips](#token-efficiency-tips)

## SKILL.md Template

Use this template as your starting point. Customize the sections based on your skill's complexity.

### Basic Template

Token-optimized: carries the five standard sections the rulebook expects (Quick Start, When to Use, When NOT to Use, Testing & Validation, Reference Guide).

Template file: `${CLAUDE_SKILL_DIR}/assets/skill-template-basic.md`

#### Token Budget Checklist

- [ ] SKILL.md under 500 lines total.
- [ ] Description uses `>-` multiline format with trigger phrases ("Use when...").
- [ ] Quick Start, When to Use, When NOT to Use, Testing & Validation, Reference Guide present.
- [ ] No YAML metadata arrays (`keywords:`, `files:`, `version:`, `argument-hint:` removed).
- [ ] No emoji section prefixes; no Priority tags.
- [ ] Complex reference material (>80 lines, <20% usage) moved to `references/` directory.

### Complex Skills Template

For complex skills requiring robust structure, add optional fields.

**Frontmatter:**

```yaml
---
name: complex-skill-name
description: >-
  What the skill does. Use when [specific trigger contexts].
  Designed for complex skill use with robust error handling.
allowed-tools: Read,Write,Bash(python:*)
---
```

**Body:**

Body template file: `${CLAUDE_SKILL_DIR}/assets/skill-template-complex-body.md`

### SKILL.md Body Structure Examples

**Minimal skill (50-75 lines):**
- Quick Start
- Workflows (2-3 bullet points)
- Key Notes

**Standard skill (75-150 lines):**
- Quick Start
- Core Workflow (steps with code)
- Variations or Advanced Options
- Key Notes
- Links to references/

**Complex skill (150-300 lines):**
- Quick Start
- Core Workflow
- Multiple workflows (conditional, template-based, etc.)
- Configuration section
- Key Notes
- Links to references/
- Troubleshooting (brief)

## Reference File Template

For skills with detailed content, create `references/complete-guide.md` or task-specific files.

Template file: `${CLAUDE_SKILL_DIR}/assets/reference-file-template.md`

## Description Formula & Examples

See `${CLAUDE_SKILL_DIR}/../../references/pdk-content-guidelines.md`'s "Writing Effective Descriptions" section for the formula, good/poor examples, and full writing rules — not repeated here to avoid drift.

## Common Description Patterns

**Action-based:**
"[Verb] [object] using [tool/method]. Use when [context]."
- "Run tests in Docker containers. Use when validating code changes."
- "Generate API documentation from OpenAPI specs. Use when creating SDK references."

**Problem-solving:**
"[Solves/prevents] [problem]. Use when [context]."
- "Prevents syntax errors in YAML configs. Use when writing Kubernetes manifests."
- "Detects unused dependencies. Use when optimizing package.json."

**Pattern-based:**
"Implement [pattern/workflow]. Use when [need/context]."
- "Implement blue-green deployments. Use when deploying without downtime."
- "Implement retry logic for flaky API calls. Use when working with unreliable services."

## Workflow Pattern Examples

### Checklist Pattern
```markdown
## Deployment Checklist
- [ ] Run tests
- [ ] Build distribution
- [ ] Update documentation
- [ ] Create pull request
- [ ] Notify team
```

### Conditional Pattern
```markdown
## Workflow: Update Dependencies

1. **Check for updates:** `npm outdated`
2. **Choose update strategy:**
   - **Minor updates only:** `npm update`
   - **All updates (test first!):** `npm install@latest`
3. **Run test suite**
4. **Commit and push**
```

### Template Pattern
```markdown
## Template: New Feature Implementation

Starting prompt:
```
I'm building [feature].
Architecture: [pattern].
Tech stack: [tools].
```

We'll follow these steps:
1. Review existing patterns
2. Design the component
3. Implement core functionality
4. Add tests
5. Document and deploy
```

### Feedback Loop Pattern
```markdown
## Workflow: Code Review

1. **Request review** with context
2. **Receive feedback** and discuss trade-offs
3. **Revise** based on feedback
4. **Iterate** until approved
5. **Merge and monitor**
```

## Optional Frontmatter Fields

Use these optional fields to customize your skill's behavior:

### Tool Scoping Examples

Apply principle of least privilege: only grant tools your skill needs.

```yaml
# Example 1: File processing skill (read/write files, run Python)
---
name: pdf-processor
allowed-tools: Read,Write,Bash(python:*)
---

# Example 2: Git workflow skill (git commands only)
---
name: git-helper
allowed-tools: Bash(git:*)
---

# Example 3: Read-only analysis (inspect code, no execution)
---
name: code-analyzer
allowed-tools: Read,Bash(grep:*),Bash(ls:*)
---

# Example 4: Skill with external dependencies (limited network, file ops only)
---
name: markdown-doc-generator
allowed-tools: Read,Write,Bash(python:*),Bash(curl:*)
---
```

**Key patterns:**
- Specify exact commands: `Bash(git:*)` not `Bash(*)`
- For team skills: minimal permissions
- Never use `Bash(*)` unless absolutely necessary

## Structure Validation

### Reference File Organization
✅ One level deep:
```
skill-development/
├── SKILL.md
└── references/
    ├── templates.md
    └── checklist.md
```

❌ Nested chains (avoid):
```
skill-development/
└── references/
    └── templates/
        └── advanced/
            └── patterns.md
```

### Filename Conventions
- **Main guide:** `complete-guide.md` or a topic name (e.g. `refinement-workflow.md`) — never bare `guide.md` or `reference.md`
- **Task-specific:** `deployment-guide.md`, `troubleshooting.md`
- **Curated lists:** `checklist.md`, `templates.md`, `patterns.md`
- **Data:** `environment-variables.md`, `hook-configuration.md` (never bare `config.md`)

## Token Efficiency Tips

### Do
- Code examples first, explanation second
- Concrete over abstract (use real project names, not "your project")
- Progressive disclosure (essentials → advanced → reference)
- Tables for structured data
- Reference other docs instead of repeating content

### Don't
- Lengthy theory before examples
- Generic placeholder names (use real examples)
- Extraneous sections (README, CHANGELOG, setup guides)
- Nested reference files (keep one level deep)
- Overly detailed troubleshooting (only high-impact issues)
