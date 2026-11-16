## Summary
`Codex delta review` re-reviews the whole PR on every push once the PR touches a gate-critical path, so the anchor-based delta narrowing never applies.

## Environment
- **Product/Service**: `.github/workflows/marketplace-ci.yml`, job `codex-review` (`Codex delta review`); `scripts/marketplace_ci/review.py`
- **Region/Version**: `main` at `7490a776`, GitHub-hosted `ubuntu-latest`
- **Browser/OS**: n/a

## Reproduction Steps
1. Open a same-repository PR whose changes include a gate-critical path, for example a file under `.github/` or `.claude-plugin/marketplace.json` (PR #750 changes `.github/workflows/mutation-testing.yml`, `.github/mutation-modules.yml` and `.claude-plugin/marketplace.json`).
2. Let one Marketplace CI run finish, so the next run has an anchor.
3. Push a commit that changes only files the gate does not care about, such as a records file under `.claude/review-outcomes/`.
4. Read the `Codex delta review` job's result: its `mode` and `reviewed_paths`.

## Expected Behavior
The run reviews only what changed since the last reviewed head, as the delta design intends (the idea #639 proposed and the anchor code now implements). If the full review is required for safety, that cost is documented.

## Actual Behavior
Every run reviews every file the PR changes against `main`, with the escalated reviewer set, for the PR's whole life. Evidence from PR #750 (2026-11-16, UTC):

| Run | Head | `ANCHOR_SHA` | Result | Job time |
|---|---|---|---|---|
| 43845390561 | `91d41e20` | `2d36c2b2` | `"mode": "full"`, all 17 PR files in `reviewed_paths` | 10:05:44-10:13:39 |
| 43847627968 | `abfc5e55` | `91d41e20` | `"mode": "full"`, all 18 PR files in `reviewed_paths` | 10:20:35-10:28:17 |

Between `91d41e20` and `abfc5e55` only `.claude-plugin/marketplace.json` and `.claude/review-outcomes/pr-750.json` changed, yet run 43847627968 reviewed `plugins/quality-kit/scripts/qlty-mutation-run.py` again and raised a blocking finding on it.

**Cause in the code:**
- `narrow_to_unreviewed` narrows to the delta only when `anchor_trust()` (`scripts/marketplace_ci/review.py:1281`) returns `"trusted"`.
- `_anchor_touches_gate()` (`review.py:1264`) makes the anchor `"untrusted"` whenever `git diff base...anchor` contains an `is_gate_critical()` path (`review.py:1080`: `FULL_ESCALATION_PATHS` or `BYPASS_INELIGIBLE_PREFIXES`) or a reviewer-steering path.
- The check reads `base...anchor`, the whole PR up to the anchor, not `anchor..head`. Once any commit of a PR touches such a path, every later anchor is untrusted until the PR merges.
- Separately, `derive_review_scope` (`review.py:330-381`) returns `mode: "full"`, the escalated reviewer set, whenever a `FULL_ESCALATION_PATHS` file such as `.claude-plugin/marketplace.json` is in the scope.

**Contributing factors seen on the same PR:**
1. **A PR-body edit costs a full review.** Each edit fires a `pull_request` `edited` event; the new Marketplace CI run cancels the one in progress and starts another full review. Run 43847569931 on `abfc5e55` was cancelled 23 seconds after it started by run 43847627968, which an edit adding an Accepted Review Findings line had triggered.
2. **A waiver clears only carried findings.** Accepted Review Findings lines are read by the "Carry forward the last review's blocking findings" step (`marketplace-ci.yml` around line 1028; `parse_waivers` and `carry_blocking_findings` in `review.py` around lines 1333-1437). A finding that a full re-review raises again counts as fresh, so the waiver does not clear it. On unchanged code the model raises such findings nondeterministically: on PR #750, a Major finding on `plugins/quality-kit/agents/mutation-tester.md:49` was raised on `91d41e20` and not on `abfc5e55`, although that file did not change between the two heads.
3. **A rebase with force-push replaces the anchor commits**, so the next run has no reachable anchor either.

## Error Details
~~~
"mode": "full",
"reviewed_paths": [ ...all files the PR changes against main... ]
~~~

## Visual Evidence
None. The run numbers and log fields above are the evidence.

## Impact
**Medium** - Every PR that touches `.github/` or a governance file pays a full review (about 8 minutes, all reviewers, all PR files) on every push and every body edit. That burns Codex usage, and findings re-raised on unchanged code block the PR nondeterministically. A workaround exists: keep gate-critical changes in their own PR.

## Additional Context
**The trust rule is deliberate and security-relevant.** A run on a PR that edits the gate's own workflow cannot prove it was reviewed by an unedited gate, so any change here needs a security review before it ships.

**Options to evaluate:**
1. Base trust on whether a gate-critical file changed between the anchor and the head, or on whether the anchor run itself used base-restored gate code, instead of on `base...anchor`. Several of the job's steps already run from code restored from the trusted base SHA; whether that covers everything the anchor's verdict depends on needs checking.
2. Keep the rule, but apply an Accepted Review Findings line to a fresh finding too when its rule, path and line match exactly.
3. Skip the re-run for an `edited` event that changed only the Accepted Review Findings section; the carry step already reads the live body.
4. At minimum, document in `docs/ci.md` that a PR touching a gate-critical path gets a full review on every push, and recommend putting such changes in their own PR.

**Related, not duplicates:** #639 (umbrella runtime investigation; this is a gap in its implemented "review only what no earlier run checked" idea), #568 (reviewer refactor), #640.
