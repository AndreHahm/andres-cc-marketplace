# Review-Finding Disclosure Report — PR #142 (Round 3)

Prepared before any merge discussion. Covers every finding handled this session (one).

## Summary

| # | Severity | Finding | Location | First seen | Decision | Merge status |
|---|----------|---------|----------|------------|----------|--------------|
| 1 | Critical | SQL injection in `build_query()` — user input concatenated directly into the query string | `db.py:210` | Round 3 (new this round) | Must fix before merge | **Blocking** |

## Detail

### 1. SQL injection in `build_query()` (Critical)

- **What was reported:** the reviewer flagged that `build_query()` builds its SQL by
  concatenating user-supplied input directly into the query string, rather than passing it
  through parameter binding.
- **Why it matters:** this is a classic, directly exploitable SQL injection pattern — an
  attacker who controls the concatenated input can alter query semantics (read data outside
  their authorization, modify/delete data, and depending on the driver/DB, potentially chain
  additional statements).
- **My assessment:** accepted as valid. This is the first round the finding has appeared in,
  so there's no prior "already addressed" or "already disputed" context to weigh — it's a
  fresh Critical/security finding and I'm treating it as credible on its face, not
  discounting it for being new.
- **Decision:** **must fix before merge.** I am not marking this resolved, deferred, or
  won't-fix. Full reasoning is in `triage.md`.
- **What I did *not* do:** I did not modify `db.py`, and I did not attempt to independently
  re-derive or "prove" the vulnerability against a real running instance — that verification
  (and the actual parameterized-query fix) is left to whoever owns that code. If, on
  inspection, the concatenated value turns out to already be a trusted/static fragment (not
  user-controlled) or is already sanitized upstream in a way not visible in this diff, that
  would be grounds to revisit this triage — but absent that evidence, the finding stands.

## Overall merge recommendation

**Do not merge PR #142 as-is.** One open Critical/security finding is outstanding with no
mitigating history. Recommended path: the author fixes `build_query()` to use parameterized
queries (or provides evidence the flagged input isn't actually attacker-controlled), the fix
gets reviewed, and only then does merge readiness get reassessed.

## Scope note

This report covers exactly the one finding surfaced in this round/session. It does not
represent a full audit of `db.py` or of PR #142 as a whole — only this specific reviewer
comment was triaged here.
