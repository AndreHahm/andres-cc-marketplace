# Installation

## 1. Deactivate OpenAI's official `codex` plugin, if installed

codex-kit bundles its own fork of that plugin's engine (broker process, job tracking, session management) rather than depending on the separately-installed plugin. Running both at once is not supported — deactivate or uninstall `codex@openai-codex` first.

## 2. Install codex-kit

```bash
/plugin install codex-kit@andres-cc-marketplace
```

Or for local development:

```bash
cc --plugin-dir /path/to/plugins/codex-kit
```

## 3. Run setup

```
/codex-kit:setup
```

This checks, and reports on explicitly:

- Codex CLI presence and version
- Node.js and npm presence
- Python 3 presence (required by the `codex-session-lookup` skill; not needed for `--persist-model`/`--persist-effort`, which are pure Node)
- `jq` presence (optional)
- Codex CLI authentication status
- Current `~/.codex/config.toml` `model`/`model_reasoning_effort` values — this is codex-kit's default model/effort source for every command and skill; nothing is written here unless you explicitly pass `--persist-model`/`--persist-effort`
- **Sandbox-mode viability** — actually attempts a trivial read-only sandboxed Codex call rather than assuming it works

If Codex CLI isn't installed and npm is available, `/codex-kit:setup` offers to install it for you.

## 4. If the sandbox check fails

Codex's read-only/workspace-write sandbox can fail on some platforms (a known Windows issue: a `CreateProcessAsUserW` access-rights error in Codex's own sandboxing subsystem). If this happens, `/codex-kit:setup` reports it explicitly and every codex-kit component will fall back to `danger-full-access` when it needs a sandbox — and will tell you every time that happens, never silently. `/codex-kit:setup` also offers opt-in guidance toward fixing the underlying access-rights issue so real sandboxing works instead of requiring full access.

## Optional: enable the stop-time review gate

```
/codex-kit:setup --enable-review-gate
```

Runs a Codex-side check on your prior turn's edits before Claude Code is allowed to stop the session, independent of and complementary to codex-kit's own double-check layer (which checks Codex's output, not the other way around).

**This gate fails closed on error, not open.** It blocks the session from stopping whenever Codex's review returns a `BLOCK` verdict, times out (up to 9 minutes), errors, or returns output that can't be parsed — in every one of those cases you're told to run `/codex-kit:review --wait` manually before the session can end. It only lets the stop through *without* a review in two narrow cases: Codex isn't set up yet (so there's nothing to run), or this is the re-continuation after the gate already blocked once for the same turn (an infinite-loop guard, not a second bypass). Because most failure modes block rather than silently pass, a Codex outage or a slow response is disruptive, not invisible — budget for the up-to-9-minute wait on every turn end while this gate is enabled.
