# Rule Development: Examples and Anti-Patterns

## Why Contrastive Examples Work

Research shows that rules with both positive and negative examples are significantly more discriminative than rules with only positive guidance. The Incorrect/Correct pairing:

1. **Eliminates ambiguity** — the agent sees the exact boundary between acceptable and unacceptable
2. **Prevents rationalization** — harder to argue "this is close enough" when the wrong pattern is explicitly shown
3. **Enables self-correction** — agents can compare their output against both patterns

## Writing Effective Rules: Extended Tables

### Description Principles

| Principle | Example |
|-----------|---------|
| **Prioritize correctness over style** | "A functionally correct but ugly solution is better than an elegant but broken one" |
| **Do not reward hallucinated detail** | "Extra information not grounded in the codebase should be penalized, not rewarded" |
| **Penalize confident errors** | "A confidently stated wrong answer is worse than an uncertain correct one" |
| **Be specific, not vague** | "Functions must not exceed 50 lines" not "Keep functions short" |
| **State the WHY** | "Use early returns to reduce nesting — deeply nested code increases cognitive load" |

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

```markdown
---
title: Use Early Returns to Reduce Nesting
paths:
  - "**/*.ts"
---

# Use Early Returns to Reduce Nesting

Handle error conditions and edge cases at the top of functions using early returns. Deeply nested code increases cognitive load and makes logic harder to follow.

## Incorrect

Guard clauses are buried inside nested conditionals, making the happy path hard to find.

\`\`\`typescript
function processOrder(order: Order) {
  if (order) {
    if (order.items.length > 0) {
      if (order.status === 'pending') {
        // actual logic buried 3 levels deep
        const total = calculateTotal(order.items)
        return submitOrder(order, total)
      } else {
        throw new Error('Order not pending')
      }
    } else {
      throw new Error('No items')
    }
  } else {
    throw new Error('No order')
  }
}
\`\`\`

## Correct

Error conditions are handled first with early returns, keeping the happy path at the top level.

\`\`\`typescript
function processOrder(order: Order) {
  if (!order) 
    throw new Error('No order')
  if (order.items.length === 0) 
    throw new Error('No items')
  if (order.status !== 'pending') 
    throw new Error('Order not pending')

  const total = calculateTotal(order.items)
  return submitOrder(order, total)
}
\`\`\`

## Reference

- [Flattening Arrow Code](https://blog.codinghorror.com/flattening-arrow-code/)
```

---

## Complete Example: Path-Scoped Rule

```markdown
---
title: API Endpoints Must Validate Input
paths:
  - "src/api/**/*.ts"
  - "src/routes/**/*.ts"
---

# API Endpoints Must Validate Input

Every API endpoint must validate request input before processing. Unvalidated input leads to runtime errors, security vulnerabilities, and data corruption.

## Incorrect

The handler trusts the request body without validation, allowing malformed data through.

\`\`\`typescript
export async function POST(req: Request) {
  const body = await req.json()
  const user = await db.users.create({
    email: body.email,
    name: body.name,
  })
  return Response.json(user)
}
\`\`\`

## Correct

Input is validated with a schema before use. Invalid requests receive a 400 response.

\`\`\`typescript
import { z } from 'zod'

const CreateUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
})

export async function POST(req: Request) {
  const parsed = CreateUserSchema.safeParse(await req.json())
  if (!parsed.success) {
    return Response.json({ error: parsed.error.flatten() }, { status: 400 })
  }
  const user = await db.users.create(parsed.data)
  return Response.json(user)
}
\`\`\`
```

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
