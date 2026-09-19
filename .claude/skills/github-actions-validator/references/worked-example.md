# Complete Worked Example: Multi-Error Workflow

This example demonstrates the **full assistant workflow** for handling multiple errors.

### User's Problematic Workflow

```yaml
name: Broken CI
on:
  schedule:
    - cron: '0 0 * * 8'  # ERROR 1
jobs:
  build:
    runs-on: ubuntu-lastest  # ERROR 2
    steps:
      - uses: actions/checkout@v3  # ERROR 3 (outdated)
      - run: echo ${{ github.event.issue.title }}  # ERROR 4 (security)
  deploy:
    needs: biuld  # ERROR 5 (typo)
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying"
```

### Example Phase 1: Run Validation

```bash
SKILL_DIR="${CLAUDE_PLUGIN_ROOT}/skills/github-actions-validator"
python3 "$SKILL_DIR/scripts/validate_workflow.py" --lint-only workflow.yml
```

**Output** (actionlint's real `file:line:col: message [rule]` format — see
`references/actionlint-usage.md`'s Output Formats section):
```
workflow.yml:4:16: invalid CRON format "0 0 * * 8" in schedule event [events]
workflow.yml:7:15: label "ubuntu-lastest" is unknown [runner-label]
workflow.yml:10:19: "github.event.issue.title" is potentially untrusted [expression]
workflow.yml:12:14: job "deploy" needs job "biuld" which does not exist [job-needs]
```

### Example Phase 2-3: Consult References and Quote Fixes (applying Steps 2-3 above)

---

**Error 1: Invalid CRON Expression**

*From `references/common-errors.md` - Schedule Errors:*

> **Cause:** Day of week 8 doesn't exist (valid: 0-6, where 0 = Sunday)
>
> ```yaml
> # Bad
> schedule:
>   - cron: '0 0 * * 8'  # Day 8 doesn't exist
>
> # Good
> schedule:
>   - cron: '0 0 * * 0'  # Sunday
> ```
>
> **CRON format:** `minute hour day month weekday`
> - Weekday: 0-6 (0 = Sunday)

**Fix:** Change `8` to `0` (Sunday) or `1-6` for Monday-Saturday.

---

**Error 2: Invalid Runner Label**

*From `references/common-errors.md` - Job Configuration Errors and `references/runners.md`:*

> **Cause:** Typo in runner label
>
> ```yaml
> # Bad
> runs-on: ubuntu-lastest  # Typo
>
> # Good
> runs-on: ubuntu-latest
> ```
>
> **Valid labels (from `references/runners.md`):**
> - `ubuntu-latest` (Ubuntu 24.04)
> - `ubuntu-24.04`, `ubuntu-22.04`
> - `macos-latest` (macOS 15)
> - `windows-latest` (Windows Server 2022)

**Fix:** Change `ubuntu-lastest` to `ubuntu-latest`.

---

**Error 3: Outdated Action Version**

*From `references/action-versions.md`:*

> | Action | Current Version | Minimum Supported |
> |--------|----------------|-------------------|
> | `actions/checkout` | **v6** | v4 |
>
> **SHA Pinning Best Practice:**
> ```yaml
> # Recommended: SHA pinning with version comment
> - uses: actions/checkout@1af3b93b6815bc44a9784bd300feb67ff0d1eeb3  # v6.0.0
> ```

**Fix:** Update from `@v3` to `@v6` (or SHA-pinned version).

---

**Error 4: Security Vulnerability (Script Injection)**

*From `references/common-errors.md` - Expression Errors:*

> **Warning:** Potential script injection via untrusted input
>
> ```yaml
> # Bad - vulnerable to injection
> run: echo ${{ github.event.issue.title }}
>
> # Good - use environment variables
> env:
>   TITLE: ${{ github.event.issue.title }}
> run: echo "$TITLE"
> ```
>
> **Why:** Untrusted input (issue titles, PR bodies, commit messages) can contain malicious commands. Using environment variables sanitizes the input.

**Fix:** Pass untrusted input through environment variable.

---

**Error 5: Undefined Job Dependency**

*From `references/common-errors.md` - Job Configuration Errors:*

> **Error:** Job 'deploy' depends on job 'biuld' which does not exist
>
> ```yaml
> # Bad
> jobs:
>   build:
>     runs-on: ubuntu-latest
>   deploy:
>     needs: biuld  # Typo
>
> # Good
> jobs:
>   build:
>     runs-on: ubuntu-latest
>   deploy:
>     needs: build
> ```

**Fix:** Change `biuld` to `build`.

---

### Example Phase 4: Provide Corrected Workflow

```yaml
name: Fixed CI
on:
  schedule:
    - cron: '0 0 * * 0'  # Fixed: Sunday (0-6 valid)
jobs:
  build:
    runs-on: ubuntu-latest  # Fixed: typo corrected
    steps:
      - uses: actions/checkout@1af3b93b6815bc44a9784bd300feb67ff0d1eeb3  # v6.0.0 - Fixed: updated version
      - name: Process issue
        env:
          TITLE: ${{ github.event.issue.title }}  # Fixed: use env var
        run: echo "$TITLE"
  deploy:
    needs: build  # Fixed: typo corrected
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying"
```

### Example Phase 5: Mandatory Rerun (applying Step 7 above)

```bash
SKILL_DIR="${CLAUDE_PLUGIN_ROOT}/skills/github-actions-validator"
python3 "$SKILL_DIR/scripts/validate_workflow.py" --lint-only workflow.yml
```

Expected rerun result:
- No previous errors reproduced
- Remaining warnings, if any, are documented explicitly

### Example Phase 6: Summary (applying Step 8 above)

| Error | Type | Fix Applied |
|-------|------|-------------|
| CRON `0 0 * * 8` | Schedule | Changed to `0 0 * * 0` |
| `ubuntu-lastest` | Runner | Changed to `ubuntu-latest` |
| `checkout@v3` | Outdated Action | Updated to `@v6.0.0` (SHA-pinned) |
| Direct `${{ }}` in run | Security | Wrapped in environment variable |
| `needs: biuld` | Job Dependency | Changed to `needs: build` |

**Recommendations:**
- Run `python3 "$SKILL_DIR/scripts/validate_workflow.py" --check-versions` regularly
- Use SHA pinning for all actions in production workflows
- Always pass untrusted input through environment variables
