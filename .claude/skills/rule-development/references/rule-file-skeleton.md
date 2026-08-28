# Rule File Skeleton

The bare Description-Incorrect-Correct template every rule file must follow.

**R18 note:** the template block is 26 content lines — Warning tier (>20, ≤30 per `plugin-rulebook/assets/settings.json`'s thresholds), not Critical. Warning recommends extraction but doesn't block; no exception is needed at this tier, and this file's own stated purpose (the exact skeleton "every rule file must follow") is the reason to keep it inline rather than extract further.

```markdown
---
title: Short Rule Name
impact: MEDIUM                  # CRITICAL | HIGH | MEDIUM | LOW
paths:                          # Optional but preferable when possible
  - "src/**/*.ts"
---

# Rule Name

[1-2 sentence description of what the rule enforces and WHY it matters.]

## Incorrect

[Description of what is wrong with this pattern.]

\`\`\`language
// Anti-pattern code or behavior example
\`\`\`

## Correct

[Description of why this pattern is better.]

\`\`\`language
// Recommended code or behavior example
\`\`\`
```

`paths` is the only field with official platform meaning; `title` and `impact` are internal plugin-devkit conventions for organizing rules, not required by the platform.
