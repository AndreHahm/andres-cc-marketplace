# Validation Writeup: examples/with-errors.yml

Skill used: `github-actions-kit`'s `github-actions-validator`
(`plugins/github-actions-kit/skills/github-actions-validator/SKILL.md`), following its own
Validation Procedure (Steps 1-8).

## What was done

1. **Tooling setup.** `act`/`actionlint` were not pre-installed on `PATH` or in
   `scripts/.tools/`. Per the skill's own Initial Setup section, installed `actionlint` v1.7.12
   into `scripts/.tools/actionlint` via its official installer script
   (`https://github.com/rhysd/actionlint#installation`) so `scripts/validate_workflow.py` could
   auto-discover it (the script checks `scripts/.tools/` before falling back to `PATH`). `act`
   was not installed — not needed, since `examples/` is outside `.github/workflows/`, and per
   the skill's own Limitations section "act can only validate workflows in `.github/workflows/`
   directory; files outside (like `examples/`) can only be validated with actionlint." Ran
   `--lint-only` accordingly.
2. **Ran `scripts/validate_workflow.py`** against `examples/with-errors.yml`, first
   `--lint-only`, then again with `--policy-checks --check-versions` for full coverage. Raw
   output saved in this directory (`script_output_lint_only.txt`, `script_output_full.txt`).
3. **Mapped each reported error** to the skill's own Step 2 mapping table and quoted the
   matching fix pattern from `references/`.
4. **Produced a corrected workflow** (`corrected-with-errors.yml`) and reran validation against
   it — clean pass, saved as `script_output_postfix_rerun.txt` (Step 7, mandatory post-fix
   rerun).

## Raw actionlint findings (--lint-only)

```
examples/with-errors.yml:18:13: invalid CRON format "0 0 * * 8" in schedule event: end of range (8) above maximum (6): 8 [events]
examples/with-errors.yml:25:14: label "ubuntu-lastest" is unknown. available labels are "windows-latest", ... "ubuntu-latest", ... [runner-label]
examples/with-errors.yml:36:36: "github.event.issue.title" is potentially untrusted. avoid using it directly in inline scripts. instead, pass it through an environment variable. [expression]
examples/with-errors.yml:39:3: job "deploy" needs job "biuld" which does not exist in this workflow [job-needs]
```

Additional findings from `--check-versions` / `--policy-checks` (advisory, no actionlint tag):
```
actions/checkout@v4 - OUTDATED (current: v6, using: v4)
examples/with-errors.yml missing explicit permissions block. Add workflow/job-level permissions (or permissions: {}).
examples/with-errors.yml:37 potential script injection risk in run step. Move untrusted input to env and quote it.
```
(The last policy-check line is the same script-injection issue actionlint already flagged at
line 36 — actionlint counts the `${{ }}` expression's column, the policy check counts the `run:`
block's line — same root cause, not a fifth error.)

## Error-to-Reference Mapping (per SKILL.md Step 2 table)

| # | actionlint output | Line | Mapping-table pattern matched | Reference file / section |
|---|---|---|---|---|
| 1 | `invalid CRON format "0 0 * * 8" ... [events]` | 18 | `cron`, `schedule` | `references/common-errors.md` -> Schedule Errors -> "1. Invalid CRON Syntax" |
| 2 | `label "ubuntu-lastest" is unknown ... [runner-label]` | 25 | `runs-on:`, `runner`, `ubuntu` | `references/runners.md` (Runner labels) + `references/common-errors.md` -> Job Configuration Errors -> "1. Invalid Runner Label" |
| 3 | `"github.event.issue.title" is potentially untrusted ... [expression]` | 36 | `untrusted`, `injection`, `security` | `references/common-errors.md` -> Expression Errors -> Script Injection Vulnerabilities (Section 3) |
| 4 | `job "deploy" needs job "biuld" which does not exist ... [job-needs]` | 39 | `needs:`, `job`, `dependency` | `references/common-errors.md` -> Job Configuration Errors -> "2. Undefined Job Dependency" |
| 5 (advisory) | `actions/checkout@v4 - OUTDATED (current: v6)` | 29 | `@v3`, `@v4`, `deprecated`, `outdated` | `references/action-versions.md` -> version table |
| 6 (advisory) | `missing explicit permissions block` | file-level | `--policy-checks` security warnings | `references/common-pitfalls.md` -> "Security Policy Checks (Advisory)" section 2 |

## Step 3: Minimal-Quote Fixes

---

**Error 1 - Invalid CRON Expression (line 18)**

From `references/common-errors.md` - Schedule Errors:
```yaml
# Bad
schedule:
  - cron: '0 0 * * 8'  # Day 8 doesn't exist

# Good
schedule:
  - cron: '0 0 * * 0'  # Sunday
```

Fix: day-of-week only runs 0-6 (0 = Sunday); `8` is invalid. Changed to `0`.

---

**Error 2 - Invalid Runner Label (line 25)**

From `references/common-errors.md` - Job Configuration Errors:
```yaml
# Bad
runs-on: ubuntu-lastest  # Typo

# Good
runs-on: ubuntu-latest
```
Valid current labels: `ubuntu-latest`, `ubuntu-24.04`, `ubuntu-22.04`, `windows-latest`, ...
see `references/runners.md` for the full list.

Fix: `ubuntu-lastest` -> `ubuntu-latest`.

---

**Error 3 - Script Injection (line 36)**

From `references/common-errors.md` - Expression Errors -> Script Injection Vulnerabilities:
```yaml
# Bad - vulnerable to injection
run: echo ${{ github.event.issue.title }}

# Good - use environment variables
env:
  TITLE: ${{ github.event.issue.title }}
run: echo "$TITLE"
```

Fix: untrusted `github.event.issue.title` moved into an `env:` var and referenced as
`"$TITLE"` inside the shell step instead of interpolated directly.

---

**Error 4 - Undefined Job Dependency (line 39)**

From `references/common-errors.md` - Job Configuration Errors:
```yaml
# Bad
jobs:
  deploy:
    needs: biuld  # Typo

# Good
jobs:
  deploy:
    needs: build
```

Fix: `needs: biuld` -> `needs: build`.

---

**Advisory 5 - Outdated Action Version (line 29)**

From `references/action-versions.md` - version table:
```
| Action | Current Version | Minimum Supported |
|--------|----------------|-------------------|
| actions/checkout | v6 | v4 |
```

Fix: `actions/checkout@v4` -> `actions/checkout@v6` (still valid as `@v4`, but `v6` is
current; upgraded for parity with the skill's own worked example).

---

**Advisory 6 - Missing Permissions Block (file-level, --policy-checks)**

From `references/common-pitfalls.md` - "Security Policy Checks (Advisory)":
> Explicit permissions - flags a workflow with no `permissions:` block at all, and
> separately flags `permissions: write-all` (prefer least-privilege scopes).

Fix: added a top-level `permissions: { contents: read }` block.

---

## Corrected Workflow

See `corrected-with-errors.yml` in this directory. Key diff summary:

| Issue | Type | Fix Applied |
|---|---|---|
| CRON `0 0 * * 8` | Schedule | Changed to `0 0 * * 0` |
| `ubuntu-lastest` | Runner label | Changed to `ubuntu-latest` |
| Direct `${{ github.event.issue.title }}` in `run:` | Security (script injection) | Wrapped via `env: TITLE:` / `"$TITLE"` |
| `needs: biuld` | Job dependency typo | Changed to `needs: build` |
| `actions/checkout@v4` | Outdated action (advisory) | Updated to `@v6` |
| No `permissions:` block | Hardening (advisory) | Added `permissions: contents: read` |

## Step 4: Unmapped Errors

None. All 4 actionlint errors and both advisory findings matched an existing row in the Step 2
mapping table.

## Step 5: Public Action Version Verification

- `actions/checkout@v4` - checked against `references/action-versions.md`: listed, current is
  `v6`, minimum supported `v4`. Not UNVERIFIED-OFFLINE (found in the offline reference table).
  Flagged OUTDATED (advisory only, not a failure).

## Step 7: Mandatory Post-Fix Rerun

Command:
```
python3 scripts/validate_workflow.py --lint-only --policy-checks corrected-with-errors.yml
```

Result (see `script_output_postfix_rerun.txt`):
```
actionlint validation passed
No security policy warnings found
All validations passed
```

No previous errors reproduced; no remaining warnings.

## Step 8: Final Summary

- 4 actionlint errors found and fixed: invalid CRON, invalid runner label, script injection,
  undefined job dependency.
- 2 advisory findings found and fixed: outdated `actions/checkout@v4`, missing
  `permissions:` block.
- 0 UNMAPPED items, 0 UNVERIFIED-OFFLINE items.
- Post-fix rerun: clean pass (see above).
- No remaining warnings/risk notes.

## Notes on this run

- `actionlint` was not pre-installed in this environment; it was installed into the skill's own
  `scripts/.tools/` directory (a location the script already checks for by convention) rather
  than system-wide, so no elevated/global install step was needed.
- `act` was not installed/run - out of scope per the skill's own documented limitation that
  `act` only validates files under `.github/workflows/`, and the target file lives under
  `examples/`.
