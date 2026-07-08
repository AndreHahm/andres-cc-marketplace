---
name: rules-review
description: >-
  Checks code changes for .claude/rules/ compliance. Use when verifying
  that code changes follow project coding rules, whether as part of
  dev-workflow or standalone. Trigger phrases — rule compliance check,
  rules review, verify conventions, check coding standards. Best suited for
  hard rules (naming, imports, placement, explicit prohibitions);
  intent-style rules are checked on a best-effort basis.
allowed-tools: Read Glob Agent Bash(git:*) ToolSearch
---

# Rules Review

Checks code changes for compliance with `.claude/rules/` rule files.

## Quick Start

1. **Ensure changed files exist** — `git diff HEAD~1 --name-only` should return files
2. **Run** — `/rules-review` (uses `HEAD~1`) or `/rules-review --base-commit <sha>`
3. **Review output** — violations are grouped by rule file with verbatim rule quote, location, description, fix, and confidence
4. **Handle drift findings** — `rule-doc-drift` entries mean the code is correct but the rule doc is stale; route to `rules-extract` rather than fixing code

## When to Use

- Before merging a PR that touches files covered by `.claude/rules/`
- After AI-assisted code generation, to verify output against project standards
- As part of a dev-workflow orchestrated by another skill
- Checking that a commit follows naming, import, and placement conventions

## When NOT to Use

- General code quality, performance, or architecture review → use a general code review skill
- Extracting new conventions into rule files → use `rules-extract`
- Project has no `.claude/rules/` directory
- Reviewing compliance of pre-existing (unchanged) code — this skill checks only diff lines

## Usage

```text
/rules-review --base-commit <sha>    # Check diff from specified commit
/rules-review                        # Check diff from HEAD~1
```

## Processing Flow

### 1. Prepare

1. Parse `--base-commit <sha>` from `$ARGUMENTS`. If not provided, use `git rev-parse HEAD~1`
2. Get changed files: `git diff --name-only <base-commit>`
3. If no changed files, output `No changed files` as the final result and exit the skill (no further steps)

### 2. Collect Rules

1. Find rule files: `Glob(".claude/rules/**/*.md")`
2. Exclude `*.examples.md` from the check targets (they are reference material, not enforceable rules)
3. If no rule files found, output `No rule files found in .claude/rules/` as the final result and exit the skill

### 3. Match Rules to Changed Files

For each rule file:

1. Read the file and parse YAML front-matter for `paths:` globs
2. If `paths:` exists: match each glob against the changed file list. If at least one changed file matches, include this rule
3. If `paths:` does not exist (e.g., `project.md`): apply to all changed files
4. Record which changed files each rule applies to

### 4. Group Rules by Category

Group matched rules into categories based on their directory path:

- **project**: Files directly under `.claude/rules/` (e.g., `project.md`, `project.local.md`)
- **{subdirectory}**: Files under `.claude/rules/{subdirectory}/` (e.g., `languages`, `frameworks`, `integrations`, or any custom directory)

Within a category, group related rules by filename prefix into families (e.g., `rails.md`, `rails-controllers.md`, `rails-models.md` = one family). Keep related rules together for consistent judgment.

Grouping policy (deterministic):
- Default: 1 group per category (one Agent per category).
- Split a category by family only when it contains more than 3 rule files, so each sub-group stays ≤ 3 files. Never split a family across groups.
- Never merge across categories, even if each category has only 1 rule file.
- Discard empty groups.

If no rules matched any changed files, output `No applicable rules for changed files` as the final result and exit the skill.

### 5. Review

Prefer parallel execution: launch one reviewer Agent per group in a single message containing multiple Agent tool calls.

Detecting Agent availability: the `Agent` tool is considered **unavailable** when its schema is not exposed in the current session's tool list (neither as a top-level tool nor via `ToolSearch`). Do not attempt a speculative call to detect availability — inspect the tool list directly.

Fallback when Agent is unavailable (e.g., this skill is itself running inside a sub-agent that cannot recurse): execute the same reviewer prompt **inline sequentially** for each group — Claude itself acts as the reviewer, reading the embedded rules/examples/diff and producing the reviewer report in a single message per group. Do not substitute `claude -p` or external CLIs; the inline path is the defined fallback. Collect results identically in both paths.

Before launching reviewers, **prepare the data to embed in each prompt** (do NOT rely on reviewers running git commands themselves):
- For each group, run `git diff <base-commit> -- <matched-files>` using the **union of files matched by any rule in that group** (so each reviewer sees every file it is responsible for, and the same file may appear in diffs for multiple groups if multiple rules match it).
- For each rule file, check if a corresponding `.examples.md` exists (same basename, e.g., `rails-controllers.md` → `rails-controllers.examples.md`) and read its content.
- If no `.examples.md` exists for any rule in the group, omit the `## Reference: Code Examples` section entirely from that reviewer prompt (do not write a placeholder line like `(no examples file)`).
- When multiple rule files are embedded in one reviewer prompt, separate them with a `### <.claude/rules/... path>` sub-heading inside the `## Rules to Check` section.

Each reviewer (Agent or inline) receives the content of `references/reviewer-prompt-template.md` as their prompt. Read that file and embed it verbatim — substituting the `<...>` placeholders with the actual prepared data.

For each reviewer:
- Set `description` to the group category name (e.g., "Review rules: frameworks") when using the Agent tool
- Embed the pre-captured diff output directly in the prompt text
- Embed the rule file contents and examples in the prompt text

### 6. Aggregate Results

1. Collect results from all reviewers (parallel Agents or inline iterations).
2. If all groups returned exactly `No rule violations found`:
   - Output: `No rule violations found` as the final result and exit the skill.
3. If violations were found:
   - Output the consolidated violation list, organized by rule file.
   - Format each violation clearly with all fields (rule file, violated rule, location, description, fix suggestion, confidence).
   - Keep `low-confidence` findings in the list with their marker preserved — do not drop them.
4. Edge cases:
   - If a reviewer returns an empty response or a response that does not match either `No rule violations found` or the violation format, retry that group once. If it fails again, include a synthetic entry in the final output under the group name with `Rule file: (review failed)`, `Description: reviewer returned unparseable output`, and continue aggregation for other groups.
   - If a reviewer returns only `low-confidence` findings (no high-confidence violations), still emit the violation list — do not substitute `No rule violations found`.

## Output Format

### When compliant

```
No rule violations found
```

> **Scope note**: This check covers only rules documented under `.claude/rules/`. Project-specific vocabulary, naming, or style conventions that have not yet been written into a rules file are out of scope — if such an unwritten convention may apply to the changed code, verify manually or run `Skill(rules-extract)` to capture the pattern as a rule. The literal output stays exactly `No rule violations found` (no extra lines) so callers that match on that string (see `§ 6. Aggregate Results`) keep working.

### When violations found

```
## Rules Compliance Violations

### .claude/rules/frameworks/rails-controllers.md

- **Violated rule**: <rule text, quoted verbatim>
- **Location**: app/controllers/users_controller.rb:15
- **Description**: <description; if quoting a bundled rule line, name the specific sub-rule>
- **Suggested fix**: <suggestion>
- **Confidence**: high

### .claude/rules/languages/ruby.md

- **Violated rule**: <rule text, quoted verbatim>
- **Location**: app/models/user.rb:42
- **Description**: <description>
- **Suggested fix**: <suggestion>
- **Confidence**: low-confidence
```

## Testing & Validation

1. **No-violation path** — run against a diff with no changes to rule-matched files; confirm output is exactly `No rule violations found` (no trailing lines)
2. **Agent fallback** — in a context where Agent is unavailable, confirm inline sequential review fires and produces the same report structure
3. **Grouping split** — with >3 rule files in one category, confirm the skill splits into sub-groups of ≤3 without splitting any family
4. **Rule-doc drift** — when code follows a different pattern than the rule across 3+ call sites, confirm `Classification: rule-doc-drift` is emitted rather than a violation
5. **Retry on parse failure** — simulate a reviewer returning unparseable output; confirm one retry fires before the synthetic failure entry is inserted

**Quality gates:**
- [ ] Each violation entry includes: rule file, violated rule (verbatim), location, description, suggested fix, confidence
- [ ] `low-confidence` findings appear in output (not silently dropped)
- [ ] `rule-doc-drift` findings include `Suggested fix: Route to rules-extract to update the rule document rather than fixing the code`
- [ ] `No rule violations found` output is exact (no extra lines) for compliant diffs
- [ ] Diff data is pre-captured and embedded in prompts, not fetched by reviewers

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/reviewer-prompt-template.md` | Verbatim reviewer prompt — read and embed in each Agent or inline review call |
