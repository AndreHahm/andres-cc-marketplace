## Summary
`cross-model-review`'s Phase 1 has no defense against Codex citing an out-of-scope `components` file — the bridge rejects Codex's *entire* envelope over one citation, unlike Phase 2 which already handles this exact case for Claude's own findings.

## Environment
- **Product/Service**: `plugins/git-kit/skills/cross-model-review` + `plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs`
- **Region/Version**: N/A

## Reproduction Steps
1. Run `cross-model-review` against a real diff that changes a function whose logic mirrors an existing pattern living in a file the diff itself doesn't touch (e.g. a new inline validation check that "should" live alongside a sibling validator in an untouched shared module).
2. Dispatch Codex's Phase 1 fresh-eyes pass with the diff's real `--target-paths`.
3. Codex — reasonably, per its own `components` field instructions ("an array of *other* file paths involved, only for a finding that's inherently about a relationship between multiple files") — cites the untouched sibling file in `components`.
4. `bridge-invoke.mjs`'s `semanticallyValidate()` calls `locateInSemanticScope` on every `components` entry, same as `location`; the untouched file fails, and the **whole envelope** is rejected with `semantic_validation_failure`.

## Expected Behavior
Phase 1 should not lose 100% of Codex's findings because one finding's `components` array cited a real-but-out-of-scope file. Phase 2 of the same skill already solves this exact problem for Claude's own findings before they're sent to Codex's challenger pass ("Drop any Claude Phase 1 finding whose `location`, or any path in its `components` array, falls on a path Preflight step 2 excluded ... before assembling this file, never pass it to Codex's challenger pass") — Phase 1 has no equivalent for Codex's own output hitting the same constraint.

## Actual Behavior
One out-of-scope `components` citation in Codex's Phase 1 response causes `bridge-invoke.mjs` to return `{"ok": false, "category": "semantic_validation_failure", ...}` for the entire dispatch. `cross-model-review`'s own resolver (step 3) then treats this as "Codex unavailable for this run" and routes to full single-model mode — discarding every other finding Codex may have found in the same pass, not just the one with the bad citation.

## Impact
**Medium** — not a crash or security issue, but it silently degrades the cross-vendor review to single-model on a plausible, reproducible input shape (a legitimate "this fix belongs in file X" observation about an untouched file), losing the whole benefit of the second reviewer for that run. Live-reproduced this session: a real PR review (branch `chore/bootstrap-marketplace-plugin-inventory`) hit this exact failure — Codex's rejected finding was almost certainly a legitimate observation about `plugins/plugin-devkit/scripts/inventory_common/reconcile.py`'s new inline `isinstance(record.get("provenance", {}), dict)` check belonging in the sibling `models.py` module (which already holds `validate_compatibility_level` for the analogous `compatibility` field) — `models.py` itself wasn't touched in the diff, so its citation was out of scope.

## Additional Context
Two independent, non-mutually-exclusive fixes to consider:
1. **Bridge-side**: when `semanticallyValidate` finds a finding whose `components` entry (not `location`) is out of scope, drop just that finding (or just that `components` entry, downgrading the finding to single-file) rather than rejecting the whole envelope. `location` failing should probably still reject the finding itself (it's the finding's primary citation), but a secondary `components` reference failing doesn't have to take everything else down with it.
2. **Skill-side** (`cross-model-review`'s own Phase 1): mirror Phase 2's own pre-filtering discipline — before treating a `semantic_validation_failure` as full Codex-unavailable, consider whether a lighter-weight retry (e.g. asking Codex to drop any `components` citation outside a stated file list) would recover a usable envelope, rather than immediately discarding everything.

Session reproduction detail: the first dispatch attempt in that same run was accidentally made with a truncated `--target-paths` (an unrelated mistake, corrected before the report above) and happened to return a validating envelope with one real, useful finding (about `example-plugin` now being installable without a test-fixture disclaimer — already tracked as #235) purely because that particular finding's location fell within the (wrongly narrow) scope given. This is incidental, not evidence against the root cause above, but is recorded here since it's a second data point that Codex's Phase 1 output for this diff was substantively useful and lost to scope rejection, not empty/low-quality.
