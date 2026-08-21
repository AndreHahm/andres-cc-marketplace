# Triage Decision — PR #142, Round 3

## Finding

> **Critical** — SQL injection possible in `build_query()` at `db.py:210` — user input is concatenated
> directly into the query string.

- **Round raised:** 3 (this is the first round this finding has appeared in — confirmed new, not a
  repeat of any round 1/2 finding; no earlier finding at this location was raised or declined, so
  dedup comparison is moot here).
- **Severity:** Critical (reviewer-stated).
- **Scope-deferred?** No — nothing indicates this is too large to fix in-session; it's a round
  classification, not a scope one.

## Classification (SKILL.md Workflow step 2-3)

1. **Dedup**: New. No prior-round finding to compare against.
2. **Round-cap routing**: Round 3+ → **Issue path** (Workflow step 5), per the two-round fix cap.
   `review_findings_severity_gate` is irrelevant to this routing decision either way — that setting
   only changes the *default* for Minor/nit findings; a Critical finding always goes through the
   fix(rounds 1-2)/file-as-issue(round 3+) pipeline regardless of the gate's value.
3. **Hard Cap exception** (`references/round-and-dedup-rules.md`): Critical/Major findings are never
   silently deferred-and-merged, in any round. Filing this as an issue is permitted — the round cap
   itself is unchanged by severity — but filing is **not** equivalent to risk acceptance. A separate,
   explicit `AskUserQuestion` confirming the risk is accepted is required before `merge-pr` runs.
4. **New-gate check**: Not applicable — this is a pre-existing code defect (SQL injection in an
   existing function), not the introduction of a new security-relevant gate, so
   `.claude/rules/require-security-review-before-new-gate.md`'s dispatch trigger doesn't fire here.

## Disposition: Issue path (not fixed in-session)

- **Not fixed this session** — round 3+ findings are never fixed in-session under this skill's cap,
  regardless of how small the fix might look; that's precisely what the Issue path exists to redirect.
- **File as a GitHub issue** (simulated — no real `gh issue create` executed per this exercise's
  constraints):
  - Title: "SQL injection in `build_query()` (`db.py:210`)"
  - Body: standard `github-issue-creator` template (Summary, Environment, Reproduction Steps,
    Expected/Actual Behavior, Impact) plus the required `## Review Finding Source` traceability
    section (`references/github-api-mechanics.md`): PR URL, head SHA, review thread/comment URL,
    reviewer, severity. **Note:** since this is a simulated PR with no real `gh` fetch performed, the
    actual PR URL, head SHA, and thread/comment ID are not available in this exercise and would need to
    be pulled from a real `gh pr view`/`gh api .../comments` call before actually filing — this triage
    stops short of fabricating those values.
  - Reference convention: plain "Found in PR #142" — never "Fixes #142"/"Closes #142", so a merge
    doesn't auto-close a still-open, unaddressed Critical issue.
- **Thread action**: reply to the finding's own inline thread pointing at the new issue number; leave
  the thread **unresolved** (deferred findings are never resolved — resolving asserts "handled," which
  this isn't).
- **Risk acceptance gate**: filing the issue does **not** satisfy the Hard Cap exception. A separate,
  explicit `AskUserQuestion` — confirming the user knowingly accepts merging with an open Critical SQL
  injection finding — is required before any `merge-pr` invocation. That question has not yet been
  asked; see `disclosure.md`.

## Round-cap tracking note

This issue-draft action, if committed on its own, is documentation-only — it does not advance the round
counter (it's not a fix-driven push), even though it does change the head SHA.
