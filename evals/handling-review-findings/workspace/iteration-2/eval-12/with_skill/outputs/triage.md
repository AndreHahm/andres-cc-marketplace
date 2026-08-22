# Triage: PR #150, Round 1

**Simulated exercise — no `gh`/API calls were executed.** Everything below is the classification and
routing decision `handling-review-findings` would apply, plus what it would post/file, described rather
than performed.

## 1. Round classification

Round 1. Both findings arrived against the current head SHA with no fix-driven push yet — per
`references/round-and-dedup-rules.md`, two reviewers (Codex, CodeRabbit) finishing at different times
against the same head SHA still belong to the same round. Well within `review_findings_max_rounds: 3`,
so no budget-exhaustion logic applies.

## 2. Dedup: one finding, not two

Per `references/round-and-dedup-rules.md`'s dedup rule, a same-file match is only a *candidate* signal —
the actual defect described must be compared. Here:

- Codex: `validate.py`'s sanitization is bypassable because three call sites each reimplement partial
  sanitization instead of routing through `sanitize_input()`.
- CodeRabbit: inconsistent sanitization across `validate.py` callers — the same architectural gap.

Both describe the identical underlying defect (inconsistent/bypassable sanitization across `validate.py`
call sites) in different words. This is classified as **one finding raised by two reviewers**, not two
distinct findings. Per SKILL.md Workflow step 5 ("Two reviewers flagging the same defect in the same
round must produce one issue, not two") and `references/testing-scenarios.md`'s matching scenario, this
resolves to a single issue with both threads pointed at it.

## 3. Exception applied: Exception 3 — too large for this session

Checking the three named exceptions in `references/settings-and-round-budget.md`:

1. Direct instruction — not present; nobody asked for this to be filed instead of fixed.
2. Out-of-scope component — not applicable; `validate.py` is squarely in this PR's own scope.
3. **Too large for this session — applies.** Both reviewers' own descriptions match this exception's
   worked examples verbatim: Codex says fixing it properly "requires tracing every call site across the
   codebase and consolidating them, not a local edit"; CodeRabbit says it "needs a data-flow audit across
   the codebase, not a text-only patch." Exception 3 is explicitly for findings needing "real data-flow
   analysis, a multi-file architectural change, or similar" — not findings that are merely tedious. This
   finding needs exactly that, so it is filed rather than attempted as a same-session fix.

This is a judgment call, not a size threshold, but both reviewers independently describing the same
codebase-wide, cross-call-site consolidation (rather than a single-file patch) is enough evidence to
route this to the Issue path rather than defaulting to attempting the fix.

**This exception is a separate, unlimited axis from the round budget** — it does not consume a
round-budget slot. Round 1's remaining budget (rounds 2–3 still available under `max_rounds: 3`) is
unaffected by this routing decision.

## 4. Issue path

- **Dedup against existing issues**: the prompt states no issue has been filed for this PR yet, so (in
  a live run) `gh issue list -R "<owner>/<repo>" --search "PR #150" --state all --limit 100` would be
  the re-check immediately before filing — simulated here as returning no match, consistent with the
  given state.
- **One issue filed**, not two, since both reviewers flagged the same defect (see Section 2).
- The issue would be drafted under `issues/YYYY-MM-DD-inconsistent-sanitization-validate-py.md`
  following `github-issue-creator`'s template, plus the traceability payload
  `references/github-api-mechanics.md` requires as a `## Review Finding Source` section:
  - PR URL: `https://github.com/<owner>/<repo>/pull/150`
  - Head SHA: the PR's current `headRefOid` (not available in this simulated exercise — would be
    resolved via `gh pr view 150 --json headRefOid` in a live run)
  - Review thread/comment URLs or IDs: Codex's inline comment thread and CodeRabbit's inline comment
    thread on `validate.py` (both cited, since both fed into this one issue)
  - Reviewers: Codex and CodeRabbit (both credited — this issue consolidates both findings)
  - Severity: Major
- Filed with a plain, non-closing reference — "Found in PR #150" — never "Fixes #150"/"Closes #150", so
  a later merge doesn't auto-close a still-unaddressed issue.

## 5. What happens to each thread

- **Codex's thread**: replied-to, pointing at the new issue number, explaining the consolidation-scope
  reasoning. **Left unresolved** — a deferred finding is redirected, not handled, so it is never resolved
  off an issue filing alone (`references/round-and-dedup-rules.md`).
- **CodeRabbit's thread**: same — replied-to pointing at the *same* issue number (not a second issue),
  left unresolved.

Neither thread is resolved, and no code change is attempted in-session for this defect.

## 6. Hard Cap interaction — Major finding on the Issue path

This is a **Major** finding routed to the Issue path via a named exception. Per
`references/round-and-dedup-rules.md`'s Hard Cap exception and SKILL.md Workflow step 3/7, a
Critical/Major finding may still legitimately end up filed as an issue (as here, via Exception 3), but
it **never proceeds to merge on the strength of the filing alone**. This must be surfaced at the
disclosure step (Workflow step 7) as a **named merge-blocking risk** requiring a separate, explicit
`AskUserQuestion` risk-acceptance before `merge-pr` is invoked for this PR — filing the issue is not
itself an acceptance of the risk.

## 7. Summary (what step 7's report would say)

- **Fixed**: nothing in this defect.
- **Filed**: 1 issue (consolidating both Codex's and CodeRabbit's Major findings on inconsistent/
  bypassable sanitization in `validate.py`), via the "too large for this session" exception. Does not
  consume round budget.
- **Declined**: nothing.
- **Merge-blocking risk flagged**: yes — this is a Major finding left unfixed and only filed; a separate
  explicit risk-acceptance `AskUserQuestion` is required before any `merge-pr` discussion, regardless of
  this PR's round-1 status or remaining round budget.
- **Round budget**: unaffected — this PR is still in round 1 of a 1–3 budget; whether to trigger round 2
  is a separate decision (Workflow step 8), not addressed by this specific finding's routing.
