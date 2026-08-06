# Slash Command Format Reference

Complete guide to creating slash commands in Claude Code plugins (`commands/` directory).

## Table of Contents

- [Command File Structure](#command-file-structure)
- [Required Frontmatter](#required-frontmatter)
- [Command Body (Instructions)](#command-body-instructions)
- [Complete Command Example](#complete-command-example)
- [Handling Missing or Optional Arguments](#handling-missing-or-optional-arguments)
- [File Organization Best Practices](#file-organization-best-practices)
- [Common Patterns](#common-patterns)
- [Metadata Guidelines](#metadata-guidelines)
- [Formatting Tips](#formatting-tips)
- [Integration with Plugin](#integration-with-plugin)

## Command File Structure

Each slash command is a Markdown file with YAML frontmatter (metadata) + instructions (body).

**File location and naming:**
```
my-plugin/
└── commands/
    ├── validate.md
    ├── report.md
    └── export.md
```

**File name becomes command identifier:**
- `validate.md` → `/my-plugin:validate`
- `report.md` → `/my-plugin:report`
- `export.md` → `/my-plugin:export`

**File format:**
```markdown
---
name: command-name
description: What Claude does when user runs this command
argument-hint: [param-name]
---

# Command Documentation

Your instructions here. Reference $ARGUMENTS (or $0, $1, ... / $param-name if using the `arguments` field) where the user's input should go.

Include examples Claude can reference and adapt.
```

## Required Frontmatter

### `name` (string)
- **Length**: 1-64 characters
- **Format**: lowercase, hyphens, no spaces
- **Purpose**: Command identifier
- **Appears in**: `/plugin-name:validate`

**Example:**
```yaml
name: validate
```

### `description` (string)
- **Length**: 1-512 characters
- **Purpose**: Explains what Claude does when command runs
- **Usage**: Claude reads this to understand the command's purpose

**Example:**
```yaml
description: Validate code against best practices and return detailed feedback with specific issues and recommendations.
```

### `argument-hint` (string, optional)
- **Purpose**: Hint shown during `/` autocomplete to indicate expected arguments
- **Format**: Free-form string, typically bracketed placeholders
- **Example**: `[issue-number]` or `[filename] [format]`

### `arguments` (string or YAML list, optional)
- **Purpose**: Declare named positional arguments so the command body can reference them by name instead of by position
- **Format**: Space-separated string or YAML list of names; each name maps to a `$name` substitution in the body, in the order the user types them
- **Not a schema**: there is no `description`/`required` per argument — Claude Code does not validate arguments before running the command, it only substitutes text. Use `argument-hint` (above) to tell the user what's expected, and handle a missing argument in the command body's own instructions

**Example:**
```yaml
name: migrate-component
description: Migrate a component from one framework to another
arguments: [component, from, to]
```
Body: `Migrate the $component component from $from to $to.`

**Without `arguments`:** the raw input is available as `$ARGUMENTS` (the full string as typed) or positionally as `$0`, `$1`, ... / `$ARGUMENTS[0]`, `$ARGUMENTS[1]`, .... If the command body doesn't reference `$ARGUMENTS` anywhere, Claude Code appends `ARGUMENTS: <value>` to the end automatically so nothing typed is lost.

## Command Body (Instructions)

Everything after the frontmatter is instructions Claude executes.

**Structure:**
```markdown
# Command Name

Brief description of what this command does.

## Quick Start

Step-by-step instructions for the most common use case.

## Examples

Concrete examples Claude can reference and adapt.

## Key Notes

Important constraints, edge cases, error handling.

## Full Reference

Detailed documentation (optional for complex commands).
```

**Guidelines:**
- Be procedural: tell Claude exactly what to do
- Be concrete: include examples, code patterns, test cases
- Be concise: focus on execution, not explanation
- Progressive disclosure: essentials first, advanced topics last

**Example command body:**

**R18 exception (recorded):** the block below intentionally exceeds the rulebook's 30-line threshold — it's a complete, coherent example command body (Quick Start + Examples + Key Notes + Language-Specific Rules together); splitting it would break the "here's what a well-formed body looks like end to end" teaching point. It uses a 4-backtick outer fence specifically so the nested 3-backtick example transcripts inside it (invocation/output pairs) nest correctly per CommonMark — a 3-backtick outer fence here would prematurely close on the first nested transcript's closing fence, the bug this block previously had.

````markdown
# Validate Command

Validate source code against best practices and return detailed feedback.

## Quick Start

1. Read the input code from `$ARGUMENTS` (or `$code` if declared via `arguments`)
2. Analyze for common issues (undefined variables, unused imports, type mismatches)
3. Check against best practices for the language given via `$language` (or auto-detect)
4. Return formatted report with:
   - Issue type (error, warning, style)
   - Line number
   - Specific issue description
   - Recommended fix
   - Priority (high, medium, low)

## Examples

**Example 1: Validate JavaScript with strict mode**
```
Invocation: /validate js --strict
Pasted code: "const x = 1; const y = 2;"

Output:
  - Line 1, col 7: Unused variable 'x' (high priority)
  - Line 1, col 22: Unused variable 'y' (high priority)
```

**Example 2: Validate Python**
```
Invocation: /validate py
Pasted code: "import os\ndef hello():\n  print('test')"

Output:
  - Line 1: Unused import 'os' (medium priority)
  - No syntax errors detected
```

## Key Notes

- If `$language` not given, attempt to auto-detect
- Always include line/column numbers in output
- Return empty report if no issues found
- Handle errors gracefully (return error message, not crash)
- Respect `--strict` if given

## Language-Specific Rules

### JavaScript/TypeScript
- Check for undefined variables, unused imports
- Validate syntax
- Flag common mistakes (== vs ===, missing semicolons if --strict given)

### Python
- Check for indentation errors
- Flag unused imports
- Validate syntax

### Go
- Check for unused variables and packages
- Validate syntax
- Format issues

### Rust
- Check for borrowing/ownership issues
- Validate syntax
- Flag common Rust patterns
````

## Complete Command Example

**File: `commands/validate.md`**

**R18 exception (recorded):** intentionally exceeds the 30-line threshold — a complete, copy-paste-ready command file, same rationale as the block above and as `examples/advanced-plugin.md`'s own recorded exception.

```markdown
---
name: validate
description: Validate source code against best practices, syntax, and style rules. Returns detailed feedback with issue location, severity, and recommended fixes.
argument-hint: [language] [rules] [--strict]
arguments: [language, rules]
---

# Validate Command

Analyzes source code for syntax errors, style violations, and best practice violations.

The code to validate is provided as $ARGUMENTS (or read from the file the user has open, if no code is pasted inline). `$language` names the language (js, ts, py, go, rust, java, c) if given — otherwise auto-detect it. `$rules` is a comma-separated list of rule categories to check (all, syntax, style, best-practices) if given — otherwise check all of them. If the user's input includes `--strict`, apply stricter style rules.

## Quick Start

1. Read the code to validate from `$ARGUMENTS`
2. Detect language (use `$language` or auto-detect)
3. Run validation checks:
   - Syntax validation (parse errors, invalid constructs)
   - Style validation (formatting, naming conventions, organization)
   - Best practice checks (unused variables, imports, common mistakes)
4. Return sorted report (high priority first)

Each issue includes:
- Line and column number
- Issue type and message
- Severity (error, warning, style)
- Recommended fix (when applicable)

## Examples

**JavaScript validation:**
```
Invocation: /validate js --strict
Pasted code: "const x = 1;"

Output:
✗ Line 1: Unused variable 'x' (error)
  Recommendation: Remove unused variable or assign to _x if intentional

✓ No syntax errors detected
✓ Code is valid JavaScript
```

**Python validation:**
```
Invocation: /validate py
Pasted code: "import os\nprint('hello')"

Output:
⚠ Line 1: Unused import 'os' (warning)
  Recommendation: Remove import or use os in code

✓ No syntax errors detected
✓ Code follows Python conventions
```

## Key Notes

- Auto-detect language if `$language` not given (by file extension or syntax)
- Return errors first (highest priority), then warnings, then style issues
- Always include line/column numbers
- Handle parse errors gracefully
- If `$rules` given, check only those rule categories
- If `--strict` given, apply stricter style rules
- Return empty result if no issues found

## Error Handling

- Invalid language: auto-detect and return warning
- Malformed code: return syntax error details
- Unknown rules: apply default rules and note skipped ones
```

## Handling Missing or Optional Arguments

Claude Code does not validate arguments against a schema before running a command — there's no `required`/`optional` enforcement. Everything is plain text substitution, so the command body's own instructions decide what to do when something expected wasn't given.

**Example with multiple named arguments:**

```yaml
name: process-file
description: Process a file and produce output in the requested format
argument-hint: <input-file> [output-format] [--verbose]
arguments: [input-file, output-format]
```
Body: `Process $input-file. Write the result as $output-format (default: json if not given). If the user's input includes --verbose, include per-step logging in the output.`

Write the body to explicitly state the default or fallback behavior for anything not marked required in `argument-hint` — that's the only place "required vs. optional" is communicated, and it's a hint to the user, not something Claude Code enforces.

## File Organization Best Practices

**Single-purpose commands:**
```
commands/
└── validate.md    # Just validation
```

**Multi-step workflow (separate commands):**
```
commands/
├── validate.md     # Step 1: validate
├── report.md       # Step 2: generate report
└── export.md       # Step 3: export results
```

**Related commands (organized by function):**
```
commands/
├── analyze.md       # Analysis commands
├── format.md        # Formatting commands
└── validate.md      # Validation commands
```

## Common Patterns

### Pattern 1: Simple Input → Output Command

```yaml
name: analyze
description: Analyze input and return results
argument-hint: <input>
```
Body: `Analyze $ARGUMENTS and return results.`

### Pattern 2: File-Based Command

```yaml
name: process
description: Process a file and generate output
argument-hint: <filepath> [options]
arguments: [filepath, options]
```
Body: `Process $filepath. Apply these options if given: $options.`

### Pattern 3: Configuration Command

```yaml
name: setup
description: Configure plugin settings
argument-hint: <config-file> [--validate-only]
arguments: [config-file]
```
Body: `Read $config-file and apply its settings. If the user's input includes --validate-only, validate the config without applying it.`

## Metadata Guidelines

**Good descriptions:**
- "Validate code syntax and style rules, returning detailed feedback"
- "Generate test reports in multiple formats with coverage analysis"
- "Extract text from PDF documents using OCR"

**Poor descriptions:**
- "Process things" (vague)
- "Do stuff" (unclear)
- "Command" (no information)

## Formatting Tips

**Use markdown for clarity:**
```markdown
---
name: command-name
description: >-
  Multi-line description if needed. Use >- for line folding
  so it stays readable in YAML.
argument-hint: <param>
arguments: [param]
---
```

## Integration with Plugin

Commands are discovered automatically if:
1. Located in `commands/` directory
2. Have `.md` file extension
3. Contain valid YAML frontmatter with `name` field
4. Plugin manifest (plugin.json) is valid

**Command activation:**
- Slash command format: `/plugin-name:command-name`
- Example: `/code-reviewer:validate`
- Claude reads command description to decide when to suggest it
