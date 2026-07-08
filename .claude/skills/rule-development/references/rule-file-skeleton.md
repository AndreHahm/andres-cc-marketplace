# Rule File Skeleton

The bare Description-Incorrect-Correct template every rule file must follow.

```markdown
---
title: Short Rule Name
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
