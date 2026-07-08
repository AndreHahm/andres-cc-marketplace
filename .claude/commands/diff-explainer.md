---
description: Explain diffs in a **human-developer-friendly** way.
---

# /diff-explainer

## Purpose

Explain diffs in a **human-developer-friendly** way.

The goal is not only to list what changed, but to explain **why the changes or deviations likely exist**, what intent they suggest, what behavior they affect, and what a developer should pay attention to.

This workflow supports GitHub PR diffs, Git branch/commit diffs, local working tree diffs, single-file diffs against a branch, and direct file-to-file diffs outside Git.

## Core Goal

For every diff, answer:

- What changed?
- Why might it have changed?
- What problem does the change appear to solve?
- What behavior, API, contract, configuration, or workflow is affected?
- Is the change structural, behavioral, stylistic, dependency-related, or risk-related?
- What should a human developer review carefully?
- Are there hidden implications or follow-up checks?

## Supported Diff Scenarios

The workflow must support these input modes:

| Scenario | Input Example | Comparison |
|---|---|---|
| 1. PR vs Main | PR number or PR URL | PR branch compared to main/base |
| 2. Git diff to Main | PR, commit, or branch | given ref compared to main |
| 3. Local diff to Branch | optional branch | local working tree compared to branch or active branch |
| 4. Local file diff to Branch | local file path + optional branch | local file compared to branch version |
| 5. File-to-file diff | two local files | file A compared to file B, independent of Git |

## Inputs

Accepted inputs:

```text
pr: <number-or-url>
commit: <commit-sha>
branch: <branch-name>
base_branch: <branch-name>
target_branch: <branch-name>
file: <local-file-path>
file_a: <local-file-path>
file_b: <local-file-path>
scope: all | staged | unstaged | file | directory
format: summary | detailed | review-oriented | teaching-oriented
include_commands: yes | no
```

Defaults:

```text
base_branch: main
target_branch: auto
scope: all
format: detailed
include_commands: yes
```

## Command Examples

### PR Diff vs Main

```text
/diff-explainer pr=123
```

```text
/diff-explainer pr=https://github.com/org/repo/pull/123
```

### Git Diff to Main

```text
/diff-explainer branch=feature/login-hardening
```

```text
/diff-explainer commit=abc1234
```

```text
/diff-explainer pr=123 base_branch=main
```

### Local Diff to Branch

```text
/diff-explainer
```

```text
/diff-explainer base_branch=develop
```

```text
/diff-explainer scope=staged
```

### Local File Diff to Branch

```text
/diff-explainer file=src/auth/session.ts
```

```text
/diff-explainer file=src/auth/session.ts base_branch=main
```

### File-to-File Diff

```text
/diff-explainer file_a=old/SKILL.md file_b=new/SKILL.md
```

## Core Rules

1. Explain intent, not only syntax.
2. Separate facts from inference.
3. Do not invent reasons when the diff does not support them.
4. Preserve file paths, symbols, function names, commands, and references exactly.
5. For inferred intent, use cautious language such as “This likely exists to...” or “This appears to...”.
6. Highlight behavioral changes before style changes.
7. Identify risk-bearing changes explicitly.
8. Mention tests, docs, migrations, config, and dependency changes when present.
9. If the diff source is ambiguous, choose the safest default and state it.
10. If a command cannot be run or required context is missing, explain what was missing and continue with available evidence.

## Workflow

See [references/diff-explainer-workflow.md]({REPO_ROOT}/.claude/references/diff-explainer-workflow.md)

Run the referenced workflow step-by-step in the defined order beginning with `Phase 1 — Detect Input Mode` and ending with `Phase 12 — Self-Review`.

## Output Format

Use this output format:

```markdown
# Diff Explanation

## Comparison

| Field | Value |
|---|---|
| Mode | |
| Base | |
| Target | |
| Scope | |
| Diff Source | |

## Short Version

Brief explanation of what this diff is about.

## Main Reason for the Changes

Explain the likely motivation or purpose.

## Changed Areas

| Area | Files | Change Type | Why It Matters |
|---|---|---|---|

## Detailed Explanation

### <Change Group>

**Observed:**  
...

**Likely intent:**  
...

**Developer impact:**  
...

**Review focus:**  
...

## Behavioral Changes

- ...

## Non-Behavioral Changes

- ...

## Risks and Review Focus

| Risk | Level | Evidence | Suggested Verification |
|---|---|---|---|

## Notable Absences

- ...

## Questions for the Author

- ...

## Commands Used / Recommended

```bash
...
```

## Final Takeaway

One short paragraph explaining what a reviewer should remember.
```

## Explanation Style

Use:

- clear headings
- short paragraphs
- developer-friendly language
- concrete file names
- specific symbols or functions when visible
- “likely” for supported inference
- “unclear” for missing context

Avoid:

- raw patch dumping
- vague summaries like “various changes”
- unsupported claims about intent
- excessive line-by-line narration
- style nitpicks unless style is the actual diff
- pretending to know PR intent when only code is available

## Special Handling

### Large Diffs

For large diffs:

1. Explain the high-level architecture of the change.
2. Group by subsystem.
3. Prioritize behavioral, security, data, and API changes.
4. Summarize repetitive mechanical changes.
5. Mention that low-risk repetitive changes were summarized.

### Generated Files

If files appear generated:

- classify as generated
- explain only the source-level reason if visible
- avoid detailed generated diff explanation
- ask whether generated files should be excluded if unclear

### Markdown and Documentation Diffs

For Markdown files:

- explain conceptual changes
- identify added, removed, or restructured sections
- preserve references and links
- highlight changed instructions or constraints
- distinguish wording cleanup from semantic changes

### Config and CI Diffs

For config, CI, Docker, or infrastructure:

- explain runtime or pipeline impact
- identify changed environment assumptions
- highlight secrets, permissions, cache, deployment, and version changes
- suggest validation commands

### Dependency Diffs

For dependency files:

- identify added, removed, updated dependencies
- explain likely purpose
- flag lockfile mismatch
- mention security or compatibility risk
- suggest audit or test command

### Security-Sensitive Diffs

If security-sensitive files changed:

- highlight auth/authz, input validation, secrets, crypto, SSRF, injection, and logging implications
- distinguish fix vs new risk
- suggest dedicated security review when needed

## Recommended Verification Suggestions

Depending on diff content, suggest:

```bash
npm test
npm run lint
npm audit
pytest
ruff check .
mypy .
dotnet test
go test ./...
cargo test
docker compose config
terraform validate
gh pr checks
```

Only suggest commands that match the visible project context.

## Error Handling

If PR metadata cannot be loaded:

```text
Could not load PR metadata. I can still explain the diff if you provide the patch or run the recommended commands.
```

If base branch does not exist:

```text
Base branch `<branch>` was not found. Please provide a valid branch or use the current branch as base.
```

If local file is missing:

```text
File not found: <path>
```

If no diff is found:

```text
No differences detected for the requested comparison.
```

If comparison mode is ambiguous:

```text
The requested comparison is ambiguous. I defaulted to <mode> because <reason>.
```

## Example Final Output Summary

```markdown
# Diff Explanation

## Short Version

This diff appears to harden the authentication flow by validating token expiry earlier, adding tests for expired sessions, and updating the login error response.

## Main Reason for the Changes

The likely motivation is to prevent expired or malformed tokens from reaching protected handlers and to make session failures easier to diagnose.

## Risks and Review Focus

| Risk | Level | Evidence | Suggested Verification |
|---|---|---|---|
| Auth behavior change | High | `auth/session.ts` now rejects tokens before user lookup | Run auth integration tests |
| Error contract change | Medium | Login now returns `SESSION_EXPIRED` | Check frontend error handling |
```
