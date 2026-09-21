## Summary
`bypass-attestation-protocol.md`'s step 4 treats the `s: codex review bypassed` label's existence as a
hard precondition for reporting a successful attestation, but an installation running with the
`CODEX_CI_REVIEW_BYPASS=1` repo variable doesn't need the label at all — its own CI-side `check_bypass`
logic resolves the attesting actor from the marker comment's real author instead of a `labeled` event.
Under that mode, a missing label makes the shared protocol report "bypass failed" even though the
marker comment posted in step 3 already made the real CI check pass.

## Environment
- **Product/Service**: `plugins/git-kit/references/bypass-attestation-protocol.md` (shared by
  `commit`/`create-pr`/`merge-pr`), consulted against `scripts/marketplace_ci/review.py`'s
  `check_bypass()`/`resolve_attested_actor()` and `.github/workflows/marketplace-ci.yml`
- **Region/Version**: this repo, found by Codex's automated review of PR #364 (round 2, 2026-09-21)

## Reproduction Steps
1. An installing repository sets its `CODEX_CI_REVIEW_BYPASS` variable to `1` (documented in
   `docs/ci.md`'s "Attesting without the label" section) and, reasonably, never creates the
   `s: codex review bypassed` label at all, since that mode doesn't need it.
2. A maintainer runs `commit --bypass-codex-review "<reason>"` (or `create-pr`/`merge-pr`'s equivalent
   flags) after pushing a commit that needs the bypass.
3. The shared protocol's step 3 posts the marker comment (`<!-- marketplace-ci-bypass-attestation
   {...} -->`) — this alone is sufficient for `resolve_attested_actor()` to accept the bypass on the
   next CI run against this exact head SHA, per `review.py`'s own logic (confirmed by direct read:
   `resolve_attested_actor()`'s docstring: "for use when no `labeled` event exists to supply a trusted
   actor... e.g. a bypass check run from a plain push rather than a label application").
4. The shared protocol's step 4 then runs `gh api "repos/{owner}/{repo}/labels/s%3A%20codex%20review%20bypassed"`
   to verify the label exists in the repo. It doesn't (per step 1's premise), so step 4 stops and
   reports the bypass as failed.
5. The next `Publish Codex policy result` CI run on this head SHA actually passes anyway, since the
   marker comment alone was sufficient under `CODEX_CI_REVIEW_BYPASS=1` — contradicting the skill's own
   "failed" report.

## Expected Behavior
The shared protocol should recognize when `CODEX_CI_REVIEW_BYPASS=1` makes the label unnecessary (e.g.
by reading the repo variable itself, or by treating "marker posted successfully" as sufficient success
criteria whenever this mode is detected/configured) and report success without requiring the label to
exist in that case.

## Actual Behavior
The label's existence is an unconditional hard gate in step 4, regardless of whether the installing
repository's own CI configuration actually requires it.

## Error Details
~~~
(no error — the failure mode is a misleading "bypass not attested" report on a bypass that actually
succeeded from CI's own perspective)
~~~

## Impact
**Medium.** Not a security gap — if anything the current behavior is over-cautious (reports failure
rather than under-reporting a real risk), and the deterministic/PR-author-privilege/branch-protection
gates this bypass never substitutes for are all unaffected either way. The impact is purely a confusing,
incorrect status report for any installation using `CODEX_CI_REVIEW_BYPASS=1` mode — a maintainer would
see "bypass not attested" and might unnecessarily retry, investigate, or manually re-attest a bypass
that already worked.

## Additional Context
This is a pre-existing design gap, not a regression introduced by PR #364 — the shared protocol
(extracted from `create-pr`'s original PR #258 implementation) has never had any `CODEX_CI_REVIEW_BYPASS`
awareness, and this repo's own current configuration has the variable set to `0` (disabled), so the gap
isn't presently biting this specific installation. Filed as a tracked issue rather than fixed reactively
in PR #364 because teaching the shared bypass-attestation protocol to understand and gracefully handle
`CODEX_CI_REVIEW_BYPASS=1` installations is a genuinely new capability, not a bounded fix to something
that PR's own changes touched — out of that PR's scope per `handling-review-findings`'s own
too-large/out-of-scope exception.

A reasonable fix shape (not prescriptive): step 4 could accept an optional caller-supplied signal for
whether label-based attestation is required at all (e.g. read via `gh api` against the repo's own
variables, or documented as a caller-resolved precondition each of `commit`/`create-pr`/`merge-pr`
passes in), and skip straight to step 5's success report when it isn't.

## Review Finding Source
- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/364
- **Head SHA**: a35357d873fb14649b3283e0e158a356dd17026e
- **Review thread/comment URL**: https://github.com/AndreHahm/andres-cc-marketplace/pull/364#discussion_r4061011780
- **Reviewer**: chatgpt-codex-connector[bot] (Codex round-2 review)
- **Stated severity**: P1 (Codex's own badge)
