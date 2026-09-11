# Plugin Component Analysis Report

**Requested scope:** billing-kit repository, full component sweep
**Inspected scope:** README.md, scripts/parse_invoice.py, logging output, persistence layer
**Unavailable evidence:** none
**Limitations:** none

## Finding A: README.md skill count is stale

**Detail:** README.md states "12 skills" in its opening summary, but the plugin currently ships 15
skills (verified via `Glob('skills/*/SKILL.md')`, 15 matches). A single-line text edit to the count in
the opening paragraph fixes it; no other content in README.md references the old count.

Severity: Minor.

## Finding B: shared invoice-parsing utility has no input validation

**Detail:** `scripts/parse_invoice.py`'s `parse_amount_field()` function is called from 12 different
call sites across the billing pipeline (verified via `Grep('parse_amount_field', '**/*.py')`, 12
matches across 6 files) and performs no validation on its input string before passing it to `float()` —
a malformed invoice line (e.g. a stray currency symbol or thousands separator) raises an unhandled
`ValueError` that crashes the entire batch job partway through, discarding already-processed invoices
in that batch. This has caused 3 separate production incidents in the last quarter per the incident
log. Fixing this requires adding validation logic, deciding on an error-recovery strategy (skip vs.
abort vs. quarantine the bad line), and updating all 6 call sites to handle the new possible
validation-failure return value consistently — there is no existing input-validation pattern elsewhere
in this codebase to follow, so the approach needs to be designed from scratch.

Severity: Major.

## Finding C: inconsistent log message capitalization

**Detail:** Log messages in `scripts/parse_invoice.py` mix "Processing invoice..." (capitalized) with
"skipping malformed line" (lowercase) inconsistently across different log statements in the same file.
Purely cosmetic — does not affect log parseability or any downstream tooling that consumes these logs.

Severity: Minor.

## Finding D: persistence layer suggested for full rewrite

**Detail:** A single edge case was found where the persistence layer (a flat-file JSON store) loses a
write if the process is killed mid-write, discovered from one specific incident where a forced VM
restart during a write corrupted one record. The specific incident is fully explained by this one
narrow race condition. A five-line fix (write to a temp file, then atomic rename) closes this exact
gap completely, matching the atomic-write pattern already used elsewhere in this codebase (e.g.
`scripts/persist_report.py`'s own write-then-rename logic). No other correctness issue was found with
the flat-file store during this analysis.

Severity: Minor (narrow, fully explained by one race condition, with an existing established fix
pattern in this same codebase already available to copy).
