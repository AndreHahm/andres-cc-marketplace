# Tool Scoping with allowed-tools

The `allowed-tools` field pre-approves the listed tools so Claude can use them without a permission prompt during the turn that invokes the skill — it does not restrict which tools are available (every tool remains callable; unlisted tools still just fall through to normal permission prompting). Implement principle of least privilege anyway: only grant tools your skill actually needs, since a broad grant skips approval prompts for actions a reviewer may want to catch.

## Syntax Formats

### Space-separated (preferred style for SKILL.md frontmatter)
```yaml
allowed-tools: Read Grep Glob
```

Note: Comma-separated (`Read,Grep,Glob`) and YAML list formats are also valid for SKILL.md frontmatter. Space-separated is the preferred canonical style, but the others are not violations.

## Available Tools (case-sensitive)

| Tool | Purpose |
|------|---------|
| `Read` | Read files |
| `Write` | Write/create files |
| `Edit` | Edit file content |
| `Bash(pattern:*)` | Execute specific bash commands |
| `Grep` | Search file contents |
| `Glob` | Find files by pattern |
| `Task` | Launch specialized agents |
| `Skill` | Invoke other skills |
| `AskUserQuestion` | Always callable regardless of `allowed-tools` (verified against current Claude Code docs: the field pre-approves permission prompts, it doesn't restrict availability) — listing it is a harmless no-op, not required and not forbidden |

## Practical Examples

### Example 1: Read-only analysis skill
```yaml
allowed-tools: Read Grep Glob
```
Use when: Analyzing code, searching files, reading documentation without modifications.

### Example 2: Python execution + file operations
```yaml
allowed-tools: Read Write Bash(python:*)
```
Use when: Processing data with Python, writing results to files.

### Example 3: Git workflow only
```yaml
allowed-tools: Bash(git:*)
```
Use when: Pure git operations (commit, push, branch management).

### Example 4: Multiple bash commands
```yaml
allowed-tools: Bash(grep:*,ls:*,find:*)
```
Use when: Shell utilities for searching and listing files.

### Example 5: Combined: bash + built-in tools
```yaml
allowed-tools: Read Glob Bash(curl:*,wget:*)
```
Use when: Fetching remote content and analyzing local files.

## Implementation Details

**Claude Code CLI only**: `allowed-tools` only works with Claude Code (not SDK)

**No restrictions by default**: If omitted, no tool restrictions apply (Claude uses standard permission model)

**Wildcard filtering**:
- `Bash(git:*)` — allows all git commands
- `Bash(python:*)` — restricts to python only
- `Bash(grep:*,ls:*)` — allows multiple specific commands

**Case-sensitive**: Use exact names (e.g., `Read` not `read`)

## Security & Best Practices

### Why allowed-tools Matters

1. **Security**: Prevent unintended tool use in sensitive workflows
2. **Clarity**: Document which tools your skill depends on
3. **Team communication**: Signal principle of least privilege to team members
4. **Production safety**: Restrict capabilities in shared or critical skills

### Choosing Tools for Your Skill

1. Identify what operations your skill performs
2. Map to minimum required tools
3. Avoid `Bash(*)` — always scope to specific commands
4. Test that the skill works with only the declared tools

### Anti-Patterns

❌ **Don't use**: `allowed-tools: Bash(*)`
- Too broad, violates principle of least privilege

❌ **Don't assume**: If tool works without `allowed-tools`, you don't need it
- Declare it explicitly for clarity

✅ **Do use**: Minimal, specific permissions
- Example: `Read Write Edit` for file-only skills
- Example: `Bash(git:*)` for git workflows

## Team Skills

For skills shared with team members:
- Always declare `allowed-tools`
- Include explanation in documentation
- Test on multiple machines
- Document any prerequisites (Python, Node.js, etc.)

Example team skill:
```yaml
---
name: team-pdf-processor
allowed-tools: Read Write Bash(python:*)
description: >-
  Process PDF files as a team. Requires Python 3.8+.
---
```
