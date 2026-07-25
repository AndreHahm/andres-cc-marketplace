# Rule File Skeleton

The bare Description-Incorrect-Correct template every rule file must follow.

**R18 exception (recorded):** intentionally exceeds the 30-line threshold — the file's own stated purpose is this exact skeleton "every rule file must follow"; trimming would contradict that.

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

`paths` is the only field with official platform meaning; `title` and `impact` are internal plugin-dev conventions for organizing rules, not required by the platform.
