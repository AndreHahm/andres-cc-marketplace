# Actionlint (rhysd/actionlint) - Usage Reference

Actionlint is a static checker for GitHub Actions workflow files that catches errors before they cause CI failures.

## Installation

See [actionlint's installation docs](https://github.com/rhysd/actionlint#installation) for the current
installation methods (Homebrew, Go install, prebuilt binaries, or the official download script). This
skill does not auto-install actionlint — see SKILL.md's Initial Setup section.

## Core Usage

### Basic Validation

Validate a single workflow file:

```bash
actionlint .github/workflows/ci.yml
```

Validate all workflow files in a directory:

```bash
actionlint .github/workflows/*.yml
```

Validate all workflows in the default location:

```bash
actionlint
```

### Output Formats

#### Default Format (human-readable)

```bash
actionlint
```

Output example:
```
.github/workflows/ci.yml:5:7: unexpected key "job" for "workflow" section [syntax-check]
.github/workflows/ci.yml:10:15: invalid CRON format "0 0 * * 8" in schedule event [events]
```

#### JSON Format

```bash
actionlint -format '{{json .}}'
```

Useful for programmatic processing and integration with other tools.

#### Sarif Format

```bash
actionlint -format sarif
```

For integration with GitHub Code Scanning and other security tools.

## Validation Categories

### 1. Syntax Checking

Validates YAML syntax and GitHub Actions schema:

- Required fields
- Valid keys and values
- Proper nesting
- Type correctness

### 2. Expression Validation

Validates GitHub Actions expressions `${{ }}`:

- Syntax errors
- Type checking (string, number, boolean)
- Function calls
- Context access

Example caught errors:
```yaml
# Error: Boolean expression expected
if: ${{ 'true' }}  # String, not boolean

# Error: Unknown function
run: echo ${{ unknown() }}

# Error: Type mismatch
if: ${{ 42 }}  # Number, not boolean
```

### 3. Runner Label Validation

Validates runner labels against known GitHub-hosted runners (standard Ubuntu/Windows/macOS, ARM64, and
GPU labels), flagging typos and retired labels.

Example:
```yaml
runs-on: ubuntu-lastest  # Error: Did you mean "ubuntu-latest"?
```

### 4. Action Validation

Validates action references:

- Action exists
- Valid version/ref
- Required inputs provided
- No unknown inputs

Example:
```yaml
# Error: Missing required input "path"
- uses: actions/checkout@v5

# Error: Unknown input "invalid_input"
- uses: actions/checkout@v5
  with:
    invalid_input: value
```

### 5. Job Dependencies

Validates `needs:` dependencies:

- Referenced jobs exist
- No circular dependencies
- Valid job IDs

### 6. CRON Syntax

Validates schedule event CRON expressions:

```yaml
# Error: Day of week must be 0-6
schedule:
  - cron: '0 0 * * 8'
```

### 7. Shell Script Validation

Integrates with shellcheck to validate shell scripts in `run:` steps:

```yaml
# Warning: Quote to prevent word splitting
run: echo $VARIABLE
```

### 8. Glob Pattern Validation

Validates glob patterns in `paths:` and `paths-ignore:` filters for structural errors (e.g., empty patterns or malformed syntax). Note: `**.js` (double-star without a slash) is not flagged by actionlint as of v1.7.x and is functionally equivalent to `**/*.js`, but `**/*.js` is the clearer, more widely understood form.

### 9. Security Checks

Detects potential security issues:

- Injection vulnerabilities
- Insecure credential handling
- Dangerous patterns

Example:
```yaml
# Warning: Potential script injection
run: echo ${{ github.event.issue.title }}
```

## Configuration

Create `.github/actionlint.yaml` or `.github/actionlint.yml`:

```yaml
# Configure shellcheck
shellcheck:
  enable: true
  shell: bash

# Configure pyflakes for Python
pyflakes:
  enable: true
  executable: pyflakes

# Ignore specific rules
ignore:
  - 'SC2086'  # Ignore shellcheck rule
  - 'action-validation'  # Ignore action validation

# Custom runner labels
self-hosted-runner:
  labels:
    - my-custom-runner
    - gpu-runner
```

## Exit Codes

- `0`: Success - no errors found
- `1`: Validation errors found
- `2`: Fatal error (invalid file, config error, etc.)

## Integration

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/rhysd/actionlint
    rev: v1.7.9  # Check https://github.com/rhysd/actionlint/releases for latest version
    hooks:
      - id: actionlint
```

**Note:** Always use the latest version of actionlint. Check the [releases page](https://github.com/rhysd/actionlint/releases) for the most recent version.

### GitHub Actions Workflow

```yaml
name: Lint GitHub Actions workflows
on: [push, pull_request]
jobs:
  actionlint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@1af3b93b6815bc44a9784bd300feb67ff0d1eeb3 # v6.0.0
      - name: Download actionlint
        # Pinned to a tagged release, not `main` — check https://github.com/rhysd/actionlint/releases for latest version
        run: bash <(curl -fsSL https://raw.githubusercontent.com/rhysd/actionlint/v1.7.9/scripts/download-actionlint.bash) 1.7.9
      - name: Run actionlint
        run: ./actionlint
```

### VS Code Integration

Install the "actionlint" extension for real-time validation in VS Code.

## Common Error Examples

See `references/common-errors.md` for the full example catalog (Job Configuration Errors, Schedule
Errors, Action Errors, Expression Errors) — the same fixes actionlint's own diagnostics above map to.

## Best Practices

1. **Run locally before pushing**: Catch errors early
2. **Use in CI/CD**: Add actionlint to your workflow
3. **Configure for custom runners**: Update config for self-hosted runners
4. **Enable shellcheck**: Catch shell script issues
5. **Review all warnings**: Even non-fatal warnings can indicate issues
6. **Keep actionlint updated**: New rules and features are added regularly

## Limitations

- Cannot validate runtime behavior (only static analysis)
- Cannot access private actions (must be public to validate)
- May not catch all possible issues (e.g., environment-specific problems)
- Custom actions may require manual verification
