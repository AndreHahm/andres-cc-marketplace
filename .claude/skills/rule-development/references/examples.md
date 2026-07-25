# Rule Development: Examples and Anti-Patterns

## Why Contrastive Examples Work

Research shows that rules with both positive and negative examples are significantly more discriminative than rules with only positive guidance. The Incorrect/Correct pairing:

1. **Eliminates ambiguity** — the agent sees the exact boundary between acceptable and unacceptable
2. **Prevents rationalization** — harder to argue "this is close enough" when the wrong pattern is explicitly shown
3. **Enables self-correction** — agents can compare their output against both patterns

## Writing Effective Rules: Extended Tables

### Description Principles

See SKILL.md's "Writing Effective Rules" section for "Be specific" and "State the WHY" — not restated here. This table covers additional principles for grading/evaluation-style rules:

| Principle | Example |
|-----------|---------|
| **Prioritize correctness over style** | "A functionally correct but ugly solution is better than an elegant but broken one" |
| **Do not reward hallucinated detail** | "Extra information not grounded in the codebase should be penalized, not rewarded" |
| **Penalize confident errors** | "A confidently stated wrong answer is worse than an uncertain correct one" |

### Incorrect Examples: What to Show

The Incorrect section must show a pattern the agent would **plausibly produce**. Abstract or contrived bad examples provide no value.

**Effective Incorrect examples:**
- Show the most common mistake agents make for this scenario
- Include the rationalization an agent might use ("this is simpler")
- Mirror real code patterns found in the codebase

**Ineffective Incorrect examples:**
- Obviously broken code no agent would produce
- Syntax errors (agents already avoid these)
- Patterns unrelated to the rule's concern

### Correct Examples: What to Show

The Correct section must show the minimal change needed to fix the Incorrect pattern.

**Effective Correct examples:**
- Show the same scenario as Incorrect, fixed
- Highlight the specific change that matters
- Include a brief comment explaining WHY this is better

**Ineffective Correct examples:**
- Completely different code from the Incorrect example
- Over-engineered solutions that add unnecessary complexity
- Patterns that require additional context not shown

---

## Complete Example: Global Rule

See `examples/global-rule-example.md` for the full worked example (Use Early Returns to Reduce Nesting).

---

## Complete Example: Path-Scoped Rule

See `examples/path-scoped-rule-example.md` for the full worked example (API Endpoints Must Validate Input).

---

## Anti-Patterns

### Vague Rules Without Examples

```markdown
# Bad: No contrastive examples, too vague
Keep functions short and readable.
Use meaningful variable names.
```

**Why bad:** No concrete boundary. "Short" means different things to different agents. No Incorrect/Correct to calibrate behavior.

### Rules That Should Be Skills

```markdown
# Bad: Multi-step procedure in a rule
When deploying to production:
1. Run all tests
2. Check coverage thresholds
3. Build the project
4. Run integration tests
5. Deploy to staging first
...
```

**Why bad:** Rules should be constraints, not workflows. This belongs in a skill.

### Duplicate Rules

```markdown
# Bad: Same guidance in two places
# .claude/rules/formatting.md says "use 2-space indent"
# CLAUDE.md also says "use 2-space indent"
```

**Why bad:** When guidance conflicts, the agent cannot determine which takes precedence. Keep each piece of guidance in exactly one location.

### Overly Broad Path Scoping

```markdown
---
paths:
  - "**/*"
---
```

**Why bad:** Equivalent to a global rule but with the overhead of path matching. Remove the `paths` field entirely for global rules.

---

## The Bottom Line

**Effective rules show, they do not just tell.** The Incorrect/Correct contrastive pattern eliminates ambiguity that prose descriptions leave open. When an agent can see both what to avoid and what to produce, compliance improves dramatically.

Every rule should answer three questions:
1. **What** behavior does this enforce?
2. **Why** does it matter?
3. **How** does right differ from wrong? (shown through contrastive examples)
