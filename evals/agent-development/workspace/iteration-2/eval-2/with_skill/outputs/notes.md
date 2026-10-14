# Review of `doc-checker` (eval 2, with skill)

Followed agent-development SKILL.md (Validate & Refine, Tool scoping, Frontmatter Fields) and ran `validate-agent.sh` on the file (saved as `doc-checker.md`). No questions to the user were needed.

## Main issue (tool scoping)
`tools: ["Read", "Grep", "Glob", "Write", "Bash"]` is over-privileged. The agent is a read-only documentation accuracy reviewer ("Read the docs and report accuracy issues") with no stated need to modify files or run commands. SKILL.md: "Read-only reviewer/analysis agents must not receive `Bash`, `Write`, or `Edit` — restrict to `Read`, `Grep`, `Glob`." Write lets it overwrite docs; Bash allows arbitrary commands. Neither is needed.

Recommended: `tools: ["Read", "Grep", "Glob"]`. If it later needs to check claims against code, Read/Grep/Glob already cover that. Add a narrow tool only with a specific justification.

## Secondary issue (description)
`description: reviews documentation for accuracy` fails the skill's convention: one sentence in the form "Use this agent when [conditions]. Typical triggers include [A] and [B]." The validator warns that it has no trigger clause. Suggested:
`Use this agent when documentation has been created or changed and needs an accuracy check. Typical triggers include a docs edit and a request to "review the docs".`

## Minor suggestions (optional)
- Body is thin (152 chars; validator suggests responsibilities, process steps, output format). Add a short Process and Output Format section.
- The `## When to invoke` bullets are fine in location (body, 2 scenarios) but could be more specific.
- Optionally add "not for code review" to the description.

## Fields that are valid (no issues)
- `name: doc-checker` (lowercase, hyphens, 3-64 chars)
- `model: inherit` (recommended default)
- `color: blue` (analysis/review convention)
- `tools` as a JSON-style array (valid format; the problem is only its contents)

## Validator output
Passed with 1 warning (missing trigger-condition clause in description).
`plugin-rulebook` was not run since no file was modified (review only).

## Suggested corrected frontmatter
```yaml
---
name: doc-checker
description: Use this agent when documentation has been created or changed and needs an accuracy check. Typical triggers include a docs edit and a request to review the docs.
tools: ["Read", "Grep", "Glob"]
model: inherit
color: blue
---
```
