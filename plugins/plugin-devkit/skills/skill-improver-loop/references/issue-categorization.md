# Issue Categorization and Evaluation

## Critical Issues (fix immediately)

Block skill loading or cause runtime failures:

- Missing required frontmatter fields (`name`, `description`) — Claude cannot index or trigger the skill
- Invalid YAML frontmatter syntax — parsing fails, skill won't load
- Referenced files that don't exist — runtime errors when Claude follows links
- Broken file paths — leads to tool failures

## Major Issues (must fix)

Significantly degrade skill effectiveness:

- Weak or vague trigger descriptions — Claude may not recognize when to use the skill
- Wrong writing voice (second person instead of imperative) — inconsistent with Claude's execution model
- SKILL.md exceeds 500 lines without using `references/` — overloads context, reduces comprehension
- Missing "When to Use" or "When NOT to Use" sections
- Description doesn't specify when to trigger — skill may never be selected
- Missing `allowed-tools` field — violates principle of least privilege
- `name` contains reserved words ("claude", "anthropic") or YAML boolean keywords
- Reference→reference chain violations — a `references/*.md` directing the reader to read another `references/` file
- Cartesian product spawning, unbounded agent spawning, or vague subagent prompts
- Undeclared tools (used in SKILL.md or a `references/` file but absent from `allowed-tools`) — causes runtime block
- Missing load-bearing key techniques for the identified workflow pattern

## Minor Issues (evaluate before fixing)

Polish items that may or may not improve the skill:

- Subjective style preferences
- Optional enhancements that add complexity without proportional value
- Formatting suggestions
- Wording changes with low functional impact

## Minor Issue Evaluation

Before implementing any minor fix:

1. **Is this a genuine improvement?** — Does it add real value or just satisfy a preference?
2. **Could this be a false positive?** — Is the reviewer misunderstanding the context?
3. **Would this actually help Claude use the skill?** — Focus on functional improvements

Only implement minor fixes that are clearly beneficial. `skill-reviewer` may produce false positives.
