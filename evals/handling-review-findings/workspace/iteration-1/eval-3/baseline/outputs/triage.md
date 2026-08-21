# Triage: PR #142, Round 3

## Finding

- **Severity:** Critical
- **Location:** `db.py:210`, function `build_query()`
- **Description:** SQL injection — user input is concatenated directly into the query string.
- **History:** First round this finding has appeared (round 3). No prior triage on record for it.

## Decision: MUST FIX — blocks merge

Rationale:

1. **Severity + vulnerability class.** SQL injection is a well-understood, high-impact,
   directly exploitable vulnerability class (data exfiltration, data corruption, auth bypass,
   in some drivers full RCE via stacked queries). Combined with a "Critical" severity label
   from the reviewer, this is not a candidate for "note and move on" or "fix in a follow-up."
2. **No mitigating history.** Because this is the first round the finding has appeared in,
   there is no prior discussion, no prior fix attempt, and no prior "won't fix" decision to
   weigh against it. It must be treated as a fresh, unverified-but-credible report, not
   dismissed as noise or a repeat of something already litigated.
3. **Standard practice for Critical + security.** Critical-severity security findings are
   treated as merge-blocking by default. Overriding that default requires an affirmative,
   documented reason (e.g., the reviewer misread non-executable/test-only code, the "user
   input" is already validated/allowlisted upstream in a way the reviewer didn't see, or the
   query builder already parameterizes and the concatenation is of trusted, static fragments
   only). No such reason is available in this session — the finding was accepted as-is.

## What happens next (author-side, not performed in this session)

- Author (or whoever owns `db.py`) rewrites `build_query()` to use parameterized
  queries / prepared statements (driver placeholders, e.g. `?`/`%s`/named params) instead of
  string concatenation, for every place user-supplied values enter the query.
- If any dynamic SQL genuinely can't be parameterized (e.g. a column/table name chosen at
  runtime), it must go through a strict allowlist, not user-controlled string interpolation.
- Re-run/re-request review on the fix before merge; do not resolve the finding on the
  strength of a promise to fix later.

## Status

**Open — blocking.** No fix has been applied in this session (per task scope: triage only,
no code changes were made). PR #142 should not be merged while this finding is open.
