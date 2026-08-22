# Triage Decision — PR #142, Codex finding on `auth/session.py:88`

**Simulated exercise — no `gh`/API calls were made.** All commands referenced below are described,
not executed.

## 1. Finding under triage

> **Minor** — `auth/session.py:88` (a file this PR never touches) has a stale docstring that still
> describes a removed parameter.
>
> Reviewer: Codex
> Round: 1 (this PR's first review after its first push-for-review; no fix-driven push has happened
> yet)
> PR scope: PR #142 changes only `billing/invoice.py`.

## 2. Round classification

Round 1 — the first (and so far only) review cycle against this PR's current head SHA. This
classification is incidental here, though: which round a finding lands in is irrelevant once one of
the three named exceptions applies, because the Issue path per those exceptions is available in *any*
round, including round 1, and never consumes a round-budget slot
(`references/settings-and-round-budget.md`, "Issue-filing is the exception"; `references/round-and-dedup-rules.md`,
"Scope-based deferral is a separate, unlimited axis from the round budget").

## 3. Exception check — which of the three named exceptions applies

Checked in order:

1. **Direct instruction** — No. Nobody (not the user, not a human reviewer) has said anything about
   how to handle this specific finding.
2. **Out-of-scope component** — **Yes, this is the one that applies.** PR #142's own changed scope is
   exactly one file, `billing/invoice.py`. The finding is against `auth/session.py:88`, a file this PR
   never touches at all. Fixing it here would mean editing a file this PR has no reason to change —
   exactly the situation Exception 2 describes ("a reviewer flags an unrelated bug in a file this PR
   doesn't touch at all").
3. **Too large for this session** — Not evaluated; Exception 2 already resolves the routing, and the
   three exceptions are independent triggers, not a ranked list requiring exhaustive elimination once
   one clearly matches. (For completeness: fixing a one-line stale docstring would not itself be "too
   large" — this finding is out-of-scope, not oversized.)

**Conclusion: Exception 2 (out-of-scope component) applies.**

This routes the finding to the **Issue path**, and that routing holds regardless of:

- **Round** — it would apply exactly the same in round 1, round 2, or round 3; Exception 2 is not
  gated by `review_findings_max_rounds` at all.
- **`review_findings_generate_issues`** — that setting only governs findings that arrive *after* the
  round budget is exhausted. It has no bearing here; Exception 2 fires independent of that setting's
  value (it's `false` in this scenario, and it still wouldn't matter if it were `true`).
- **Severity** — the finding is only Minor, but severity does not affect whether an out-of-scope
  finding gets filed. A Minor out-of-scope finding is filed exactly like a Critical or Major
  out-of-scope finding would be; the Hard Cap exception (Critical/Major findings never silently
  proceed) is about *what happens once something is filed* (a required risk-acceptance gate before
  merge), not about whether out-of-scope routing itself depends on severity. Since this finding is
  Minor, the Hard Cap's extra merge-blocking disclosure requirement does not apply, but the Issue-path
  routing decision itself is unaffected by severity either way.

**This finding is explicitly NOT attempted as an in-session fix.** Even though a one-line docstring
correction would be trivially easy, and even though round 1 would otherwise have plenty of fix-budget
room, ease-of-fix is not a factor in this decision — Exception 2 exists precisely to keep this PR's
diff scoped to what it actually set out to change (`billing/invoice.py`), not to expand into unrelated
files just because a reviewer happened to notice something nearby.

## 4. Dedup check (Issue path, Workflow step 5)

Before drafting a new issue, the real workflow would run:

```
gh issue list -R "<owner>/<repo>" --search "PR #142" --state all --limit 100
```

— `--state all` so an already-closed duplicate isn't invisible, `--search "PR #142"` because every
issue this skill files always includes that exact "Found in PR #142" text, and never an unqualified
`gh issue list` (30-issue default cap). This is a simulated exercise with no real repository to query,
so this check is described rather than executed; assuming (as this scenario implies — no prior issue
exists for this finding) the search returns no match, a new issue is drafted and filed below.

## 5. Drafted GitHub issue

File: `issues/2026-08-22-stale-docstring-auth-session.md` (to be committed alongside — or, if nothing
else is being committed this round, as a documentation-only commit on its own).

```markdown
## Summary
Stale docstring in `auth/session.py:88` still describes a parameter that has since been removed.

## Environment
- **Product/Service**: (this repository)
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
1. Open `auth/session.py` and read the docstring at line 88.
2. Compare the documented parameter list against the function's actual current signature.
3. Observe that the docstring still names a parameter that was removed from the signature.

## Expected Behavior
The docstring at `auth/session.py:88` should describe only the parameters the function actually
accepts today.

## Actual Behavior
The docstring still documents a parameter that no longer exists on the function, which will mislead
anyone reading it as reference documentation.

## Error Details
~~~
(none — this is a documentation accuracy issue, not a runtime error)
~~~

## Visual Evidence
N/A

## Impact
Minor — no functional or runtime effect; a misleading docstring is a low-severity documentation
defect, but worth tracking since it can cause a future caller to pass or expect the wrong parameters.

## Additional Context
Flagged by Codex during PR #142's round-1 review. Filed as a separate issue rather than fixed in PR
#142 because `auth/session.py` is entirely outside PR #142's own changed scope (that PR touches only
`billing/invoice.py`) — see Exception 2 ("out-of-scope component") in
`handling-review-findings`'s settings-and-round-budget reference.

## Review Finding Source
- **PR URL**: https://github.com/<owner>/<repo>/pull/142
- **Head SHA**: `<head-sha-of-PR-142-at-time-of-finding>` (the commit PR #142 was at when Codex posted
  this finding)
- **Review thread/comment**: <inline-review-comment-URL-or-ID for Codex's comment on
  `auth/session.py:88`>
- **Reviewer**: Codex
- **Severity**: Minor
```

Filed with:

```
gh issue create -R "<owner>/<repo>" --title "Stale docstring in auth/session.py:88 references a removed parameter" --body-file <scratchpad-path>/issue-body.md
```

## 6. Non-closing PR reference text

Exactly:

```
Found in PR #142
```

Never `Fixes #142` or `Closes #142` — this issue is unrelated to what PR #142 actually changes, and a
non-closing reference is required so merging PR #142 doesn't auto-close this still-open,
still-unaddressed issue.

## 7. Reply posted to Codex's review thread

```
Thanks for flagging this — `auth/session.py` is outside this PR's own scope (PR #142 only changes
`billing/invoice.py`), so this is being tracked separately rather than fixed here: #<new-issue-number>.
Leaving this thread open until that issue is addressed.
```

(`#<new-issue-number>` is the real issue number `gh issue create` returns once actually filed — not
knowable in this simulated exercise since no real `gh` call is made.)

## 8. Thread resolution

**The thread is left unresolved.** It is not resolved now, and it will not be resolved by this PR at
all — resolving it would assert "this is handled," but the finding was redirected to a separate issue,
not handled here. Per `references/round-and-dedup-rules.md` ("Already-fixed threads get resolved with
commit-SHA evidence; deferred ones don't get resolved at all") and
`references/github-api-mechanics.md` ("Leaving a thread unresolved on purpose"): reply with the
tracking-issue reference (step 7 above), and simply never call `resolveReviewThread` for this thread.
An issue filed with no trace on the PR would read as the finding being silently dropped, so the reply
is required even though the thread stays open.

## Summary of disposition

| Item | Decision |
|---|---|
| Round | 1 |
| Exception applied | Exception 2 — out-of-scope component |
| Path | Issue (never attempted as an in-session fix) |
| Dedup check | `gh issue list --search "PR #142" --state all --limit 100` — assumed no match in this scenario |
| Issue filed | Yes, with full traceability payload (PR URL, head SHA, thread reference, reviewer, severity) |
| PR reference text | `Found in PR #142` (non-closing) |
| Thread reply | Points at the new issue number |
| Thread resolved? | **No — left unresolved** |
