# Triage: PR #142 — `tmp2` non-descriptive variable name (`utils.py:88`)

**Note on scope:** this is a simulated exercise. No `gh`/API calls were made. All
PR/SHA/thread/reviewer values below marked `<...>` are placeholders standing in for values that
Workflow step 1's live re-fetch (`gh pr view`, `gh pr checks`, `gh api .../pulls/{n}/comments`)
would normally supply immediately before acting — per
`.claude/rules/recheck-state-before-side-effecting-action.md`, that re-fetch is a hard precondition
on any real side-effecting call, and is explicitly not performed here since there is no real PR.

## 1. Triage decision

**Finding:** Minor — variable name `tmp2` in `utils.py:88` is non-descriptive.

**Settings read:** `review_findings_severity_gate` = `false` (default; per the task's own framing,
this is the value in effect — the git-tracked `git-kit.settings.json` default, no overriding
`.claude/git-kit.local.json` field assumed).

**Round classification: Round 3.**
Why: the task states this finding was never raised in round 1 or round 2, and per
`references/round-and-dedup-rules.md`'s dedup mechanism, a finding is "new" only if it wasn't
already raised (and fixed, or explicitly declined) in an earlier round. There is no round 1/2
candidate at `utils.py:88` (or anywhere else) describing this same defect — the non-descriptive
name of the `tmp2` variable — to compare content against, so there is no location *or* content
match to collapse it into. It is genuinely new in round 3, not a re-raised repeat carried forward
from an earlier round. (Per the same reference: when a content comparison is genuinely uncertain,
the rule is to default to "new" rather than "repeat" — that default isn't even needed here, since
there's no earlier-round finding at this location to compare against in the first place.)

**Severity:** Minor (reviewer-stated, taken at face value — nothing here suggests Critical/Major,
so the Hard Cap exception in `references/round-and-dedup-rules.md` does not apply).

**Scope-deferred?** No — this is a trivial rename, not a finding too large to fix in-session. Scope
deferral is irrelevant to its routing; the round number alone determines the path here.

**Path selected: Issue path (Workflow step 3 → step 5).**
Reasoning, per SKILL.md Workflow step 3: scope-deferred findings always go to the Issue path
regardless of round (not applicable here — this isn't scope-deferred). Otherwise: round 1/2 →
Fix path, *unless* the severity gate is `true` and the finding is Minor/nit with nobody explicitly
requesting the fix, → Decline path. **Round 3+ → Issue path, with that same Minor/nit exception
routing to Decline instead — but only when the gate is `true`.** Here the gate is `false`, so the
Minor/nit-decline carve-out never activates; the plain round-3+ rule governs and this finding goes
to the **Issue path**, not Fix and not Decline. (If the gate had been `true` instead, this exact
same Minor finding would route to Decline — reply-only, no issue filed — per SKILL.md's Settings
section and the testing-scenarios.md worked case for `severity_gate: true` + Minor + round 1; that
scenario doesn't apply here since the gate is `false`.)

No explicit request to fix this specific finding was made by the user or a human reviewer, so no
override applies (moot here anyway, since the override only matters under `severity_gate: true`).

**Dedup-against-existing-issues check (Workflow step 5, first bullet):** before drafting, the real
run would execute `gh issue list` scoped to this PR/head-SHA to confirm no existing issue already
covers this same defect (e.g. filed by a duplicate finding from a second reviewer in the same
round). Not executable in this simulated exercise — assumed clean (no existing duplicate) for the
purposes of drafting the issue below; a real run must perform this check before filing.

**Disposition:** File as its own tracked GitHub issue (draft below). Reply to the finding's own
review thread pointing at the new issue number. **Leave the thread unresolved.** This is not a
Critical/Major finding, so Workflow step 7's additional `AskUserQuestion` risk-acceptance
requirement does not apply — but the routine disclosure step (fixed/filed/declined report) still
applies before any merge discussion.

---

## 2. Drafted GitHub issue body

File path (if this were real): `issues/2026-08-21-tmp2-non-descriptive-variable-name.md`

```markdown
## Summary

Variable name `tmp2` in `utils.py:88` is non-descriptive and should be renamed to something that
conveys its purpose.

## Environment

- Repository: `<owner>/<repo>` (resolved from PR #142 at triage time)
- File: `utils.py`
- Line: 88

## Reproduction Steps

1. Open `utils.py` at line 88.
2. Observe the variable name `tmp2`.

## Expected/Actual Behavior

- **Expected:** Variable names communicate intent or content, especially for names that persist
  beyond a one-line scratch use.
- **Actual:** The variable is named `tmp2`, which conveys neither its type nor its role, and
  implies (via the `2` suffix) an unexplained relationship to some other `tmp`-named variable
  elsewhere in the same function/module.

## Impact

Low. Purely a readability/maintainability nit — no functional defect, no security or correctness
impact. Filed rather than fixed in-session solely because this PR is in its third review round and
the round cap (see `references/round-and-dedup-rules.md`) routes round-3+ findings to an issue
regardless of how small the fix would be, so a future contributor can pick it up without it
blocking or re-extending this PR's review cycle.

## Additional Context

Found during PR #142's third review round. Not a repeat of any round 1/2 finding — no earlier round
raised a defect at this location or of this kind.

## Review Finding Source

- **PR:** `<PR URL — e.g. https://github.com/<owner>/<repo>/pull/142>`
- **Head SHA:** `<head SHA the finding was raised against — from a live `gh pr view --json headRefOid` at triage time>`
- **Review thread/comment:** `<review thread or comment URL/ID — from a live `gh api repos/{owner}/{repo}/pulls/142/comments` at triage time>`
- **Reviewer:** `<reviewer tool/handle that raised this finding>`
- **Severity:** Minor
```

**Filing command (not executed — reference only):**
```
gh issue create --title "Variable name tmp2 in utils.py:88 is non-descriptive" \
  --body-file issues/2026-08-21-tmp2-non-descriptive-variable-name.md
```

---

## 3. Non-closing PR reference text

Per `references/github-api-mechanics.md`'s Issue-filing convention — plain, non-closing, so a
merge doesn't auto-close a still-open, still-unaddressed issue:

```
Found in PR #142
```

(Never `Fixes #142` / `Closes #142`.)

---

## 4. Exact reply text for the review thread

Posted via `gh api repos/{owner}/{repo}/pulls/142/comments/{comment_id}/replies` once the issue
above is actually filed and its real issue number is known (shown here as `#<ISSUE_NUMBER>`):

```
This is genuinely new in round 3 of review — not a repeat of anything raised in rounds 1-2. Per
this repo's review-findings policy, round 3+ findings are filed as tracked issues rather than
fixed in this PR, regardless of severity. Filed as #<ISSUE_NUMBER> (variable name `tmp2` in
utils.py:88 is non-descriptive). Leaving this thread open until that issue is addressed.
```

---

## 5. Thread resolution

**The thread is NOT resolved.** Per SKILL.md Workflow step 5 and
`references/round-and-dedup-rules.md`'s "Already-fixed threads get resolved with commit-SHA
evidence; deferred ones don't get resolved at all": resolving a thread asserts the finding is
handled, and a filed-not-fixed finding is redirected, not handled. `resolveReviewThread` is
intentionally never called for this thread. The reply above states explicitly that the thread is
being left open until the linked issue is addressed, per
`references/github-api-mechanics.md`'s "Leaving a thread unresolved on purpose" guidance.

---

## Report (Workflow step 7 disclosure)

**Filed, not fixed:** 1 finding — `tmp2` non-descriptive variable name (`utils.py:88`), Minor,
round 3. Filed as issue `#<ISSUE_NUMBER>` (draft: `issues/2026-08-21-tmp2-non-descriptive-variable-name.md`).
Thread replied-to, left unresolved. No Critical/Major findings deferred this run, so no additional
`AskUserQuestion` risk-acceptance is required before a subsequent `merge-pr` run — but this
still-open thread must be named explicitly if/when `merge-pr` readiness is discussed, since
`merge-pr`'s own check isn't scoped to notice it. This disclosure is informational only; it does
not itself determine or imply mergeability.
