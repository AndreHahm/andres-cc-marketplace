## Summary
A `cross-model-review` re-run's Codex finding was discarded by `bridge-invoke.mjs`'s own semantic validation because it cited a file outside the declared `--target-paths` scope — the finding's actual content was never surfaced, only its rejected citation.

## Environment
- **Product/Service**: `codex-kit` plugin (this marketplace) — `codex-review-bridge/scripts/bridge-invoke.mjs`'s `semanticallyValidate`, invoked via `git-kit`'s `cross-model-review` skill
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
1. Run `cross-model-review`'s Phase 1 Codex dispatch (`bridge-invoke.mjs --execution-profile read-only`) with `--target-paths` set to the diff's own changed-file list only (per the skill's documented Preflight step 2 — "changed files only", never files merely read for context).
2. Codex reviews the diff, and in doing so reads an existing, unchanged file for context (here: `plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs` itself — imported by the diff's own modified `guarded-dispatch.mjs`, but not itself part of the diff against `main`).
3. Codex's returned finding cites that file in its `location`/`components` field.
4. `semanticallyValidate` rejects the entire envelope: `{"ok":false,"category":"semantic_validation_failure","detail":"finding F1 cites an out-of-scope or nonexistent component: <path>"}`.

## Expected Behavior
Either: (a) the caller can distinguish "off-topic citation, safe to fully discard" from "a citation about a file the diff's own changed code directly depends on, worth preserving in some form even if flagged as out-of-scope", or (b) the rejection response still surfaces the finding's own `finding`/`evidence` text (redacted of any out-of-scope specifics if needed) so a human reviewer isn't left with zero information about what was actually found.

## Actual Behavior
The entire envelope is discarded on any single out-of-scope citation — including the finding's own `finding`/`evidence` prose, which is never returned to the caller. A caller has no way to recover or triage the substance of a rejected finding; the only signal is the cited path itself.

## Impact
**Low** — no security exposure (this is the validation working as designed: Codex cannot get a caller to trust a citation about a file outside the declared review scope). The impact is coverage/usability: a plausibly-real finding about how the diff's own changed code interacts with an unchanged, directly-imported dependency is lost entirely rather than degraded gracefully.

## Additional Context
Found live during a `create-pr` → `cross-model-review` gate re-run on `codex-kit`'s downstream QA branch (`fix/codex-kit-downstream-qa`, 2026-08-24), after fixing an earlier confirmed finding (a missing `Bash(git branch --show-current:*)` grant on `codex-audit-loop`). The rejected citation (`plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs`) is directly imported by this same diff's modified `guarded-dispatch.mjs` (`ENVELOPE_SCHEMA`, `semanticallyValidate`, `isValidToken`, `neutralizeClosingTags`), so the finding may well have been about that exact interaction — but its content is unrecoverable from this session.

Not yet decided/prioritized: whether the fix belongs in `cross-model-review` (widen `--target-paths` to include files the diff's own changed code directly imports, not just files literally changed in the diff), in `bridge-invoke.mjs`'s `semanticallyValidate` (return the rejected finding's prose alongside the `ok:false` envelope, clearly marked out-of-scope, rather than discarding it), or is working as intended and just needs documenting as a known limitation.

Filed live: https://github.com/AndreHahm/andres-cc-marketplace/issues/111
