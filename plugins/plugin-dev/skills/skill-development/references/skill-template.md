# Skill Template (Token-Optimized)

Copy the structure below to start a new skill. Follow the progressive loading system for maximum token efficiency.

```markdown
---
name: {skill-name}
description: >-
  {What it does — start with action verbs}. Use when {primary trigger conditions}:
  {keywords}, {trigger phrases}, {file patterns}. {Optional: explicit scope or constraints}.
allowed-tools: Read Edit Write Glob
---

# {Skill Name}

{One-line imperative summary of what to do}.

## Quick Start

1. **{Step 1}** — {brief instruction}
2. **{Step 2}** — {brief instruction}
3. **{Step 3}** — {brief instruction}

## When to Use

- {Primary trigger condition}
- {Secondary trigger condition}
- {Specific scenario where this skill applies}

## When NOT to Use

- {Exclusion 1} → use `{alternative-skill}` instead
- {Exclusion 2} → {reason or alternative approach}

## {Core Workflow}

{Procedural steps or rules for the main use case.}

- **{Rule 1}**: {Imperative constraint}.
- **{Rule 2}**: {Imperative constraint}.

---

## Testing & Validation

1. **{Check 1}** — {what to verify}
2. **{Check 2}** — {what to verify}

**Quality gates:**
- [ ] {Gate 1}
- [ ] {Gate 2}

---

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/{file}.md` | {What it contains and when to read it} |
```

## Token Budget Checklist

- [ ] SKILL.md under 500 lines total.
- [ ] Description uses `>-` multiline format with trigger phrases ("Use when...").
- [ ] Quick Start, When to Use, When NOT to Use, Testing & Validation, Reference Guide present.
- [ ] No YAML metadata arrays (`keywords:`, `files:`, `version:`, `argument-hint:` removed).
- [ ] No emoji section prefixes; no Priority tags.
- [ ] Complex reference material (>80 lines, <20% usage) moved to `references/` directory.
