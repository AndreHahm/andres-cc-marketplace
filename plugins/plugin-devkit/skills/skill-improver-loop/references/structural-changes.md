# Structural Change Rules

Apply these rules when a fix requires reorganizing content, moving sections, or extracting to `references/`.

## Pre-Change Gates (run in order before any structural change)

1. **Content Audit** — List ALL existing content. Classify as core (80%+ of activations) or supplementary (<20%). Nothing gets deleted without classification first.
2. **Capability Assessment** — Will this change impair skill execution? If YES → migrate only, never delete.
3. **Migration Verification** — Before moving content, verify the destination file exists and is complete. No gaps allowed.
4. **Auto-approve check** — In automated (no-questions) mode: auto-approve migrations; skip deletions not fully verified through gates 1–3.

## Movement Pattern (never violate order)

```
1. CREATE/UPDATE destination file(s) with merged content
2. LINK — update SKILL.md pointers to new destination
3. DELETE old source (only after links verified)
```

NEVER: `DELETE → LINK → CREATE` — creates broken links and loses content.

## 80% Rule (content placement)

- **Core content (80%+ of activations)** → stays in `SKILL.md`
- **Supplementary content (<20% of activations)** → can move to `references/`
- **Uncertain?** → keep in `SKILL.md` by default

Apply when fixing "SKILL.md too long" or "consolidate references" issues. Never move content solely to reduce line count if execution is affected.
