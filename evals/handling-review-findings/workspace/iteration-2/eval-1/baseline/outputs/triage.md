# Triage: PR #142 — Codex finding on `parse_config()`

## Finding under review

> **Major** — `parse_config()` at `config.py:47` doesn't handle a missing `timeout` key and raises
> `KeyError` instead of falling back to the documented default.

## 1. Which round does this belong to?

This is **round 1** — the finding was posted by Codex as the first review after the PR's first
push-for-review, and no fix has been pushed yet that would close out a round. There's nothing here
that would push it into a later round; it's simply the first finding of the first round.

## 2. Fix, file, or decline?

**Fix.** Reasoning:

- Severity is **Major**, and `review_findings_severity_gate` is `false` (the default), so there's no
  reason to auto-decline this as a nit — a Major correctness bug doesn't get waved through.
- The finding is about `config.py`, a file within this PR's own change surface (nothing suggests this
  is an out-of-scope file the PR never touched).
- It is a small, well-scoped, local fix (add a `.get("timeout", DEFAULT_TIMEOUT)`-style fallback, or an
  explicit `try/except KeyError`) — not the kind of cross-cutting, multi-file architectural change that
  would justify treating it as "too large for this session."
- Nobody has given an explicit instruction to file this instead of fixing it, and there's no reason to
  believe this needs to be deferred.
- We are in round 1, well within any reasonable round/attempt budget, so there's no budget-exhaustion
  concern either.

So this is a straightforward **Fix** — no exception route (no out-of-scope routing, no "too large,"
no explicit user instruction to file, no budget exhaustion) applies here.

## 3. What happens to the review thread?

**Verification is a hard precondition before any reply or resolve action.** Concretely, before doing
anything to the thread:

1. Implement the fix in `config.py` — make `parse_config()` fall back to the documented default
   `timeout` value when the key is missing, instead of raising `KeyError`.
2. Add or update a test that exercises the missing-`timeout` case, confirming it now returns the
   documented default rather than raising.
3. Commit the change with a clear, conventional commit message (e.g.
   `fix(config): fall back to default timeout when key is missing`), and push it to the PR branch.
4. **Re-verify the fix against the actual finding** — re-read the diff and confirm: (a) the `KeyError`
   no longer occurs when `timeout` is absent, and (b) the value used in that case matches the
   *documented* default, not just some arbitrary fallback. Run the test suite (or at minimum the new/
   updated test) and confirm it passes.

**Only after that verification actually passes** do we touch the thread at all:

- **Reply text to post to the thread** (posted only once the fix is pushed *and* verified):

  > Fixed in `<commit-sha>` — `parse_config()` now falls back to the documented default timeout when
  > the `timeout` key is missing, instead of raising `KeyError`. Added/updated a test covering the
  > missing-key case and confirmed it passes.

  (The literal `<commit-sha>` is filled in with the actual short SHA of the fixing commit once it
  exists — it is never posted as a placeholder, and the reply is never posted before that commit
  exists and has been verified.)

- **Resolve the thread:** the thread is resolved **only after** that reply is posted, and **only
  because** verification actually confirmed the fix is correct. It is explicitly **not** resolved on
  the strength of a pushed commit alone — a commit that merely *claims* to address the finding, without
  having been re-checked against the finding's specific description, is not sufficient grounds to
  reply or resolve. If verification were to fail (e.g., the fallback value doesn't match the documented
  default, or the fix misses an edge case), the thread would stay open, unresolved, with no reply
  posted, until the fix is corrected and re-verified.

## Summary

| Question | Answer |
|---|---|
| Round | Round 1 |
| Disposition | Fix (no exception applies) |
| Precondition before reply/resolve | Fix must be committed, pushed, and independently re-verified against the finding |
| Reply text | "Fixed in `<commit-sha>` — `parse_config()` now falls back to the documented default timeout when the `timeout` key is missing, instead of raising `KeyError`. Added/updated a test covering the missing-key case and confirmed it passes." |
| Thread resolution | Resolved only after the reply is posted, and only because verification passed — never resolved on an unverified push |
