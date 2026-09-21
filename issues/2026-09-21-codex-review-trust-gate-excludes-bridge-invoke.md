## Summary
`codex-review`'s hard-refuse trust-boundary gate covers only Python files under `scripts/marketplace_ci/` — it does not cover `bridge-invoke.mjs` or repo-root Codex/agent context files, which are also part of the review-dispatch path

## Environment
- **Product/Service**: Claude Code plugin marketplace (`andres-cc-marketplace`), `.github/workflows/marketplace-ci.yml` — the `codex-review` job's "Refuse automated Codex dispatch when this PR modifies review-dispatch-critical code (trust boundary)" step
- **Region/Version**: n/a (CI workflow)

## Reproduction Steps
1. Read `scripts/marketplace_ci/review.py`'s `dispatch_reviewers()` — it invokes `plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs` as a Node subprocess, which itself spawns the `codex` CLI.
2. Read the `codex-review` job's "Refuse automated Codex dispatch when this PR modifies review-dispatch-critical code (trust boundary)" step in `.github/workflows/marketplace-ci.yml` — its `git diff --quiet` pathspec list covers only `scripts/__init__.py`, `scripts/marketplace_ci/{__init__,__main__,review,git_state,registry,sync_plan,conversion,pr_policy}.py`, `pyproject.toml`, and `uv.lock`.
3. Observe `bridge-invoke.mjs` itself, its own dependencies, and any repo-root Codex/agent context files (e.g. `.codex/config.toml`) are absent from that list.

## Expected Behavior
The gate's own error text states it protects "the same code this job dispatches reviewers with... the very code that decides and reports this review's own outcome" — a same-repo PR editing any part of that dispatch path (Python or otherwise) should trip the same hard-refuse gate, or be restored from the trusted base SHA the way the Tier 1 Python modules now are (see #351).

## Actual Behavior
A same-repo PR that edits only `bridge-invoke.mjs` (e.g. to always report a clean pass, or to exfiltrate reviewed diff content) does not trip this gate at all — the PR's own, unverified copy of the script runs unchecked.

## Impact
**Medium** — not an active exploit (requires a malicious or compromised same-repo contributor with PR-open rights), but a real, currently-live gap in the review-dispatch trust boundary's actual coverage. Not introduced by #351's own Tier 1/Tier 2 split (the gap predates it, under the old blanket `scripts/`-only gate too), but adjacent to and structurally similar to what #351 already addresses for the Python side.

## Additional Context
Surfaced by a `security-reviewer` pass on the PR implementing #351's direction #3 (splitting `scripts/marketplace_ci/` into a Tier 1 review-dispatch-critical module set vs. Tier 2 apply-side tooling). This is a decision-tracking issue, not a prescribed fix — open question: should `bridge-invoke.mjs` (and/or repo-root Codex context files) join the gate's own pathspec/restore logic, or does some other mitigation apply?

Refs #351
