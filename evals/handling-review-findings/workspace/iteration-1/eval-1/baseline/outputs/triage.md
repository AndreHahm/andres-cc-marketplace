# Triage: PR #142, Round 1 — Codex finding on `parse_config()`

## Finding under triage

> **Major** — `parse_config()` at `config.py:47` doesn't handle a missing `timeout` key and
> raises `KeyError` instead of falling back to the documented default.

## Round

**Round 1** (this is the first review after the PR's first push-for-review — there is no
earlier round for this finding to belong to, and no reason to defer it to a later round).

## Triage decision: FIX

Rationale:

- The finding describes a concrete, verifiable correctness bug: the code's actual behavior
  (raise `KeyError` on a missing key) contradicts its own documented behavior (fall back to a
  default). This isn't a style preference, a false positive, or a matter of taste — it's a
  functional defect with a clear reproduction (call `parse_config()` on input missing
  `timeout`).
- Severity is Major, and it's round 1 — the cheapest and most appropriate point in the review
  lifecycle to fix a real bug, before any other round's findings stack on top of it or before
  the PR is merged with broken fallback behavior.
- The fix is narrow and low-risk: use `dict.get("timeout", DEFAULT_TIMEOUT)` (or equivalent
  `.get()`/`try`-`except KeyError` handling) instead of direct key access, restoring the
  already-documented contract. No design discussion or scope negotiation is needed.
- Not a candidate for "file as a follow-up issue" — it's small enough to fix in this same PR,
  and shipping it unfixed would leave a Major-severity bug in code this PR is actively
  introducing/touching.
- Not a candidate for "decline" — there's no disagreement with Codex's read of the code; the
  documented default is the intended behavior and the current implementation doesn't honor it.

**Action taken:** Fix `parse_config()` in `config.py` (around line 47) to fall back to the
documented default timeout value when the `timeout` key is absent from the config, instead of
letting the dict lookup raise `KeyError`. Add or update a test covering the missing-key case to
confirm the fallback fires and no exception is raised.

## Reply to post to the review thread

> Good catch — confirmed. `parse_config()` was doing a direct `config["timeout"]` lookup, so any
> config missing the key raised `KeyError` instead of falling back to the documented default.
> Fixed in config.py:47 by using `.get("timeout", DEFAULT_TIMEOUT)` and added a test for the
> missing-key case. Will push the fix as a follow-up commit on this branch.

## Thread resolution

**Not resolved yet.** The thread stays open until the fix commit is actually pushed to the PR
branch and the reply above has been posted. Once the fix commit lands:

1. Push the commit containing the `parse_config()` fix and its test.
2. Verify the pushed diff actually addresses `config.py:47` as described (don't resolve on the
   strength of intent alone).
3. Only then mark the thread resolved — resolution should follow visible evidence of the fix in
   the PR's commit history, not precede it. Resolving before the fix is pushed would leave a
   thread marked "handled" while the branch still contains the bug.
