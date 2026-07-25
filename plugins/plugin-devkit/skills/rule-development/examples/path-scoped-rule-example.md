# Complete Example: Path-Scoped Rule

A full worked example of a path-scoped rule file, referenced from `references/examples.md`. This is the content of `.claude/rules/api-input-validation.md`.

**Frontmatter:**
```yaml
title: API Endpoints Must Validate Input
impact: CRITICAL
paths:
  - "src/api/**/*.ts"
  - "src/routes/**/*.ts"
```

# API Endpoints Must Validate Input

Every API endpoint must validate request input before processing. Unvalidated input leads to runtime errors, security vulnerabilities, and data corruption.

## Incorrect

The handler trusts the request body without validation, allowing malformed data through.

```typescript
export async function POST(req: Request) {
  const body = await req.json()
  const user = await db.users.create({
    email: body.email,
    name: body.name,
  })
  return Response.json(user)
}
```

## Correct

Input is validated with a schema before use. Invalid requests receive a 400 response.

```typescript
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
```
