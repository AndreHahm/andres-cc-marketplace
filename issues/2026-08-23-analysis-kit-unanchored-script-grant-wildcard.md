## Summary
Every `Bash(python .../scripts/<name>.py:*)` grant across `analysis-kit`'s skills (and, per a quick spot-check, other plugins in this marketplace) uses a leading `*` wildcard path segment (e.g. `Bash(python */analysis-kit/scripts/session_parser.py:*)`) rather than an anchored `${CLAUDE_PLUGIN_ROOT}`-based path, even though every actual invocation site in the body uses the anchored form. Whether this is a real permission-scoping gap depends on unverified behavior of Claude Code's own permission matcher.

## Environment
- **Product/Service**: all `analysis-kit` skills' `allowed-tools` frontmatter (10 skills with script grants); the same pattern appears to be this marketplace's general convention, not analysis-kit-specific
- **Region/Version**: this repo, found during `plugin-lifecycle-downstream`'s Phase 5 Audit (security-reviewer finding sec-M6) on a run scoped to `fix/analysis-kit-downstream-qa`

## Reproduction Steps
1. Compare any `analysis-kit` skill's frontmatter grant, e.g. `Bash(python */analysis-kit/scripts/session_parser.py:*)`, against its body's actual invocation, e.g. `Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/session_parser.py" ...)`.
2. Note the leading `*` in the grant is not anchored to the plugin root — per a literal reading, a path ending in `/analysis-kit/scripts/session_parser.py` anywhere else in a checkout would also satisfy the grant.
3. Try to verify whether Claude Code's real permission matcher treats `${CLAUDE_PLUGIN_ROOT}` as resolvable/comparable against a `*`-prefixed grant pattern, and whether the matcher additionally tolerates a shell-operator suffix (`;`, `&&`) after the trailing `:*)` — this requires live execution against the actual permission system, not static text review.

## Expected Behavior
Either (a) confirm the wildcard form is intentionally broad and safe given how the real matcher works, or (b) narrow every grant to the tightest literal prefix the actual install layout supports, once that's known.

## Actual Behavior
No change was made — the finding was deferred as accepted risk specifically because narrowing the grant syntax blind, without first confirming how the permission matcher actually resolves `${CLAUDE_PLUGIN_ROOT}`-style paths against a `*`-prefixed grant, risks silently breaking every script grant in the plugin (all 10 script-invoking skills) with no way to detect the breakage until a live run fails.

## Impact
**Low, pending verification** — this is a defense-in-depth concern (an over-broad grant boundary), not a demonstrated live exploit; no analysis-kit skill's own body ever invokes a script from outside its own `${CLAUDE_PLUGIN_ROOT}`. The real question is scoping precision, not an active vulnerability.

## Additional Context
- This is a marketplace-wide convention, not something specific to `analysis-kit` — fixing it in one plugin without the same treatment elsewhere would create inconsistency rather than resolve the underlying question.
- Per this repo's own `.claude/rules/verify-tool-behavior-before-instructing.md`, the correct next step is to verify the actual permission-matcher behavior first (via `ToolSearch`/the tool's own schema, or a live one-off grant test), not to guess and hand-edit grant syntax repo-wide.
- Suggested follow-up: once verified, decide whether this is worth a repo-wide sweep (all plugins, not just `analysis-kit`) or whether the current wildcard form is already the marketplace's deliberate, accepted convention.
