## Summary
Add a second, diff-only reviewer pass to `Codex delta review`, so a PR that changes review-dispatch-critical (Tier-1) code gets an automated review instead of only a manual bypass

## Environment
- **Product/Service**: `.github/workflows/marketplace-ci.yml`, `codex-review` job, step "Refuse automated Codex dispatch when this PR modifies review-dispatch-critical code (trust boundary)"; `scripts/marketplace_ci/review.py`
- **Region/Version**: `main` at 9750c68c

## Reproduction Steps
1. Open a same-repo PR that changes a Tier-1 file: `scripts/__init__.py`, `scripts/marketplace_ci/{__init__,__main__,review,review_contract,review_verifiers,git_state,registry,sync_plan,conversion,prefix_check,pr_policy}.py`, `pyproject.toml`, `uv.lock`, the uv and Python-version config, the codex-kit Node bridge files, `token_shapes.json` or `review_exceptions.yaml` (full list in `docs/ci.md`, Tier 1).
2. Observe that `Codex delta review` refuses the PR.
3. The only way to merge is the manual SHA-bound bypass attestation.

## Expected Behavior
A Tier-1 change gets an automated review that the change itself cannot tamper with, in addition to the maintainer's own review.

## Actual Behavior
Tier-1 changes get no automated review at all: the job refuses them, and the maintainer's manual review and bypass attestation are the only check. Restoring the Tier-1 files from the base SHA (#351, direction 1) was rejected because it hides the PR's real changes from the reviewer.

## Impact
**Low** - The manual bypass is a working, safe default; this adds an automated safety net, it does not unblock anything.

## Additional Context
Split out of #351 (direction 2). #351 is closed because directions 3 (Tier-1/Tier-2 split) and 4 (`--bypass-codex-review` in `commit`, `create-pr` and `merge-pr`) shipped.

Proposal: a second, independent reviewer pass, run from trusted base-SHA code, that sees only a diff/patch representation of the Tier-1 changes.

Requirements:
- Real isolation: the PR's Tier-1 files must not be readable on disk by the dispatch code or the reviewer. Passing the patch as extra context next to the real files is not enough.
- A new reviewer prompt built for reviewing diff text.
- `publish` wiring that reuses the existing envelope validation.
- A requirement entry in `docs/ci-codex-review-user-requirements.md`, approved by the maintainer before implementation.
- Tests proving the isolation holds, not only that the dispatch runs.
- A `security-reviewer` pass before the first commit (`.claude/rules/require-security-review-before-new-gate.md`): this is a new trust-boundary gate.

Residual risk, even done right: a diff crafted to read as benign to a model. This narrows the need for human review of Tier-1 code but does not remove it.

Estimate (from #351's analysis): several days; the highest cost and the most novel mechanism of the directions considered.

Related: #351, #568 (reviewer refactor), #620 (standalone attestation on an already-pushed head), #713.
