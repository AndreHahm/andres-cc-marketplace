# Eval 1 (with_skill) notes

Task: create a read-only agent `agents/test-coverage-checker.md` that reports changed PR functions lacking tests.

Skill followed: agent-development/SKILL.md (Quick Start, frontmatter rules, Required Agent Sections, Manual Creation), plus assets/template-plugin-agent.md.

Decisions / assumed answers:
- Structured Output Mode question (AskUserQuestion): assumed "read by a person only", so none added (skill says not to add speculatively).
- Delta Mode question: assumed no; agent's scope is the PR's given changed files, already narrow.
- Tools: `["Read", "Grep", "Glob"]` only; no Write/Edit/Bash. Because there is no Bash, the agent takes the changed-file list/diff from the caller.
- Model `inherit`, color `cyan` (analysis/review).
- Description: one sentence-style "Use this agent when ... Typical triggers include ...", no `<example>` blocks, in `>-` block scalar (R8 flagged the one-line form at 234 chars).
- Body: Title, Identity, Goal, Input, Load Context, Process (self-critique last), Output Format, Constraints, then `## When to invoke` with 4 prose bullets.
- Output Format code block was replaced with a numbered list after the R18 advisory (>10-line code block).

Verification:
- `validate-agent.sh`: all checks passed (before the later edits; the edits only touched the description's YAML form and the output-format section).
- PostToolUse rulebook hook (deterministic subset R4-R6, R8, R9, R13, R14, R17, R18): initially FAIL R8 + ADVISORY R18, both fixed; final run clean.
- Full `Skill(plugin-rulebook)` was NOT run (eval sandbox); the semantic rules R1-R3, R7, R10, R19-R22 remain unchecked.
- Did not re-run validate-agent.sh after the final edits.

Skill observations: the file output path `agents/test-coverage-checker.md` was written under outputs/agents/ as instructed by the harness; no files under plugins/ or .claude/ were modified.
