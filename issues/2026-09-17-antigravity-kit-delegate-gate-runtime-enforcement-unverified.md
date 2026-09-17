## Summary
antigravity-kit's delegation gate may not be honored at runtime at all

## Environment
- **Product/Service**: Claude Code plugin marketplace (`andres-cc-marketplace`), `plugins/antigravity-kit/hooks/agy-validate-delegate-bash.sh` and `plugins/antigravity-kit/agents/antigravity-delegate.md`
- **Region/Version**: `antigravity-kit` v0.1.0

## Reproduction Steps
1. `agy-validate-delegate-bash.sh` is registered only in `agents/antigravity-delegate.md`'s own frontmatter `hooks:` block — it is not listed in `plugins/antigravity-kit/hooks/hooks.json`.
2. Both the hook's own header comment and the agent file already state that this repository's platform documentation says hooks declared in a *plugin-scoped* agent's own frontmatter are accepted by the schema but not honored at runtime.
3. If that holds, install this plugin for real and have the `antigravity-delegate` subagent attempt a command this gate is meant to block (e.g. a disallowed pipe producer).
4. Observe whether the command is actually blocked, or whether it runs unimpeded because the declared `PreToolUse` hook never fires.

## Expected Behavior
Either the gate demonstrably fires and blocks disallowed commands in a real installed copy of the plugin, or the plugin's own documentation should stop describing it as "defense-in-depth" and instead describe the agent's `tools:` grant as the sole real boundary.

## Actual Behavior
Unverified. If the frontmatter-hook limitation holds, the entire delegation gate — including the #336 cat-removal fix and its follow-up hardening — is inert in a real installed copy of the plugin, and the actual security boundary is just the agent's `tools:` grant (which includes unscoped `Bash`).

## Impact
**Medium-High (unverified)** — this is not a new defect introduced by any recent change; both files already disclose the uncertainty. It's flagged here because it materially bounds how much assurance the gate (and any future hardening of it) actually buys, and that bound has never been live-verified against a real installed copy of the plugin.

## Additional Context
Found by an independent `security-reviewer` pass during the #336 fix. Rated Major. Needs live verification against an installed copy of the plugin. If confirmed inert, the gate should either be registered in `hooks/hooks.json` under a `PreToolUse`/`Bash` matcher (which would apply session-wide, not just to the subagent — a real behavior-scope tradeoff to weigh) or the defense-in-depth framing should be dropped in favor of describing `tools:` as the sole real boundary. This is a decision/investigation-tracking issue, not an implementation request.
