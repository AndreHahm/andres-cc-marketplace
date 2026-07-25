# Templates for Skill Creation

**R18 exception (recorded):** several templates below intentionally exceed the rulebook's 30-line code-block threshold — each is a complete, copy-paste-ready template; splitting one would break its usability. Matches this plugin's established R18 exception pattern (see `command-development/references/marketplace-considerations.md`).

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

### Basic Template (Minimal)

````markdown
---
name: skill-name
description: >-
  What the skill does. Use when [specific trigger contexts].
  [Optional: key constraints or scope].
---

# Skill Name

## Quick Start
[Minimal example showing immediate usage. Code-first, 5-10 lines.]

```bash
# Example command or workflow
command example here
```

## Core Workflow
[Main 3-5 step workflow. Imperative style: "Do X", "Run Y", "Configure Z"]

## Advanced Options
[Optional: specific variations, edge cases, configuration]

## Key Notes
- Important assumption or constraint
- Common gotcha or best practice
- Deployment location or integration point

## Full Reference
For detailed configuration, see `references/complete-guide.md`
````

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

````markdown
# Skill Name

## Overview
[Brief description of what this skill does]

## Prerequisites
- Required software/libraries: Python 3.8+, requests library
- Environment variables (required):
  - `GITHUB_TOKEN`: Personal access token from https://github.com/settings/tokens
  - `API_ENDPOINT`: Your API endpoint URL
- Validation: Run `bash scripts/validate-env.sh` to verify setup

## Quick Start
[3-5 step usage with example]

## Common Workflows
- [Workflow 1]
- [Workflow 2]
- [Workflow 3]

## Validation
Run the validation script to test the skill:

```bash
bash scripts/validate-env.sh  # Verify environment setup
bash scripts/validate.sh      # Full skill validation
```

## Error Handling
[How the skill handles failures and what error messages mean]

## Security Notes

This skill requires credentials. Never hardcode them:

**Required environment variables:**
- `API_KEY`: Get from https://service.com/api-keys
- `SECRET_TOKEN`: Get from https://service.com/settings

**Setup:**
```bash
export API_KEY=your_key_here
export SECRET_TOKEN=your_token_here
bash scripts/validate-env.sh  # Verify setup
```

**See `references/secrets-and-credentials.md` for complete security guidance.**

## Troubleshooting
[Common issues and solutions]

## Support
Contact: [Team lead / owner]

## Version History
See [VERSION_HISTORY.md](../VERSION_HISTORY.md)
````

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

```markdown
# Complete Guide: [Skill Name]

## Table of Contents
- [Configuration](#configuration)
- [Operations](#operations)
- [Workflows](#workflows)
- [Troubleshooting](#troubleshooting)

## Configuration

### Environment Variables
| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| VAR_NAME | Yes | — | Description |
| VAR_NAME | No | default_value | Description |

### File Structure
```
project/
├── config.yml
├── src/
└── tests/
```

## Operations

### Basic Operation
[Step-by-step instructions with code examples]

### Advanced Operation
[For users who understand the basics]

## Workflows

### Template: [Workflow Name]
[Checklist or step-by-step workflow]

## Troubleshooting

### Error: [Error Message]
**Cause:** Explanation
**Solution:** Fix steps
```

## Description Formula & Examples

See `content-guidelines.md`'s "Writing Effective Descriptions" section for the formula, good/poor examples, and full writing rules — not repeated here to avoid drift.

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
allowed-tools: Read,Bash(grep:*,ls:*)
---

# Example 4: Skill with external dependencies (limited network, file ops only)
---
name: markdown-doc-generator
allowed-tools: Read,Write,Bash(python:*,curl:*)
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
skill-creator/
├── SKILL.md
└── references/
    ├── templates.md
    └── checklist.md
```

❌ Nested chains (avoid):
```
skill-creator/
└── references/
    └── templates/
        └── advanced/
            └── patterns.md
```

### Filename Conventions
- **Main guide:** `complete-guide.md`, `guide.md`, or `reference.md`
- **Task-specific:** `deployment-guide.md`, `troubleshooting.md`
- **Curated lists:** `checklist.md`, `templates.md`, `patterns.md`
- **Data:** `config.md`, `environment-variables.md`

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
