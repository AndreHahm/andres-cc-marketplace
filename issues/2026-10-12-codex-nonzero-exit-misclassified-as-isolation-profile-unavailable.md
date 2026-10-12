## Summary
Any non-zero Codex exit that is not an auth or unknown-option error is reported as `isolation_profile_unavailable`, because the classifier matches the word "sandbox" in Codex's own banner; the real error is then cut off before it reaches the CI log.

## Environment
- **Product/Service**: `codex-kit` (`plugins/codex-kit/scripts/lib/codex-exec.mjs`), marketplace CI (`scripts/marketplace_ci/review.py`)
- **Region/Version**: Codex CLI 0.147.0 (CI pin), `main` at `8ef5d419`
- **Browser/OS**: Linux (GitHub-hosted runner and a local Linux machine)

## Reproduction Steps
1. Set the repository variable `CODEX_KIT_REVIEW_MODEL` to a model that Codex cannot serve (observed with `gpt-6-luna`).
2. Open or update a PR so the `Codex delta review` job dispatches the four reviewers.
3. Read the job log and `codex-review-result.json`.

## Expected Behavior
The failure names its real cause (capacity, model rejected, rate limit), or at least is not classified as a sandbox problem. The log keeps the end of Codex's stderr.

## Actual Behavior
All four reviewers return `isolation_profile_unavailable` after one attempt, about 49 seconds into dispatch. The preceding bwrap sandbox workaround step passed. The detail shows only echoed reviewer-prompt text. Allowlisting the model on the OpenAI platform and re-running changed nothing; switching the variable back to `gpt-5.6-luna` made the same job run and return real findings. An earlier local run showed `ERROR: Selected model is at capacity` in the stderr behind the same category.

## Error Details
~~~
Cause 1 (mislabel): codex-exec.mjs, close handler, ~line 527
  /CreateProcessAsUserW|sandbox|permission denied|access is denied/i.test(stderr)
  is tested against the WHOLE stderr. Codex always prints a banner with "sandbox: read-only",
  so every non-zero exit not caught earlier by the auth or unknown-option checks matches.
  Synthetic stderr (banner + capacity error): auth=false unknown=false isolation=true

Cause 2 (cause truncated): the bridge keeps the tail (slice(-4000)), but Codex echoes the whole
  reviewer prompt into stderr, so the tail starts mid-prompt. review.py ~line 1600 then keeps
  the HEAD: _sanitize_log_text(stderr)[:_MAX_ERROR_CHARS] with _MAX_ERROR_CHARS = 2000 (~line 1388).
  A detail whose real cause is at the end loses it under head-2000 (verified).
~~~

## Visual Evidence
None. CI run 38234368524 and 38237121566, job logs of `Codex delta review` on PR #542.

## Impact
**Medium** - the Codex CI gate fails with a misleading category and no usable cause. `isolation_profile_unavailable` is the category the resolver treats as a trigger to fall back to a wider sandbox, so a capacity or model error is routed toward privilege widening.

## Additional Context
Not proven: what the actual error was for `gpt-6-luna` in CI (capacity versus the model being rejected for the API key). The real cause was never visible, which is the defect.

Proposed fix:
- Anchor the isolation pattern to real sandbox failures (known phrases, banner line excluded, or classify on the last lines only).
- Give capacity and model errors their own category, or report them as `non_zero_exit` with the detail.
- Keep the tail of stderr in `review.py` and strip the echoed prompt.
- Add tests for banner plus capacity stderr.

Constraint: `codex-exec.mjs`, `review.py` and `__main__.py` are review-dispatch-critical (Tier-1, `scripts/marketplace_ci/trust_boundary.py`). CI hard-refuses automated Codex dispatch on a PR that changes them, so the fix needs the manual bypass path or the redesign in #351.

Related: #543 (same Tier-1 files; `run-codex-review` cannot redirect its scratch directory), #351 (trust-boundary gate redesign), #163 (a different false-positive path in `isTotalInspectionFailure`, the zero-exit Windows case; not a duplicate), #78 (closed, Windows dispatch), #540 and PR #542 (where this was found).
