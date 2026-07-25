# Key Rules (Non-Negotiable)

The four invariants that govern every refinement change. `SKILL.md`'s own workflow steps already apply these — this file is the full-detail reference, not a separate procedure to follow independently.

## The 80% Rule (Content Distribution)
- Will Claude execute this in 80%+ of skill activations? → **STAYS in SKILL.md**
- Will Claude execute this in <20% of cases? → **CAN MOVE to references/**
- Uncertain? → **DEFER to operator; keep in SKILL.md by default**

See `references/80-percent-rule.md` for the full decision framework.

## Movement Pattern (for content changes)
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

See `references/movement-pattern.md` for the full safe-migration procedure.

## Preservation Gates (Four Gates, In Order)
1. **Content Audit** - List ALL existing content. Classify using **the 80% rule**: core content (used in 80%+ of activations) vs. supplementary (<20%). See `references/80-percent-rule.md` for full decision framework.
2. **Capability Assessment** - Will changes impair execution? If YES → cannot delete, only migrate
3. **Migration Verification** - Before moving, verify destination complete. NO GAPS
4. **Operator Confirmation** - Deletions require explicit approval. Migrations auto-approved

See `references/preservation-rules.md` for what never gets cut and `references/refinement-guardrails.md` for safe patterns.

## Scope Rules (Where to Work)
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
