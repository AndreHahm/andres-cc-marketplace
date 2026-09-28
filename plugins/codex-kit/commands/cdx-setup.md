---
description: >-
  Check Codex CLI readiness, sandbox viability, and config; optionally
  toggle the stop-time review gate
argument-hint: '[--enable-review-gate|--disable-review-gate] [--persist-model <slug>] [--persist-effort <level>]'
disable-model-invocation: true
allowed-tools: Bash(node */codex-kit/scripts/codex-companion.mjs:*), Bash(npm install -g @openai/codex), AskUserQuestion
---

> **Invocation:** Run as `/codex-kit:setup` in the Claude Code prompt. This command cannot be invoked via `Skill()` — it must be triggered as a slash command.

Raw slash-command arguments: `$ARGUMENTS`

Validate `$ARGUMENTS` against the whitelist in the `argument-hint` above (`--enable-review-gate`, `--disable-review-gate`, `--persist-model <slug>`, `--persist-effort <level>`) before running anything — do not interpolate the raw argument string into a shell command. Parse it yourself, reject/`AskUserQuestion` on anything unrecognized, then pass only the validated, individually-quoted flags:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs" setup --json
```

(append validated `--enable-review-gate`/`--disable-review-gate`/`--persist-model "<value>"`/`--persist-effort "<value>"` flags as separate, quoted arguments to the command above — never as a single unquoted `$ARGUMENTS` blob.)

This reports, every time, on: Codex CLI presence/version, Node/npm presence, Python 3 presence (required by the codex-session-lookup skill, not by `--persist-*` — that path is pure Node), `jq` presence (optional), Codex authentication status, current `~/.codex/config.toml` `model`/`model_reasoning_effort` values, and whether Codex's read-only sandbox actually works on this platform.

If Codex is unavailable and npm is available:
- Use `AskUserQuestion` exactly once to ask whether Claude should install Codex now.
- Options, install first and `(Recommended)`: `Install Codex (Recommended)` / `Skip for now`.
- If install: run `npm install -g @openai/codex`, then rerun the setup script above.

If the report's sandbox check shows the sandbox is NOT working:
- **Never treat this as resolved or silently move on.** State plainly that every codex-kit component will fall back to `danger-full-access` when it needs a sandbox, and will say so explicitly every single time that happens — this is not a one-time warning.
- Offer, via `AskUserQuestion`, opt-in guidance toward fixing the underlying issue rather than living with the fallback: options `Show me how to fix this` / `Not now`. If chosen, explain (for Windows) that this is a `CreateProcessAsUserW` access-rights failure in Codex's own sandboxing subsystem — point the user to Codex CLI's own documentation/issue tracker for the current recommended fix for their platform, since the exact remediation steps are version-dependent and owned by Codex CLI, not by this plugin.

If the user passed `--persist-model` or `--persist-effort`:
- **Confirm via `AskUserQuestion` before running the script with those flags.** This writes to the user's global `~/.codex/config.toml`, affecting every other tool that invokes the Codex CLI directly, not just this session. Show exactly what will change (current value → requested value) before asking.
- Only after confirmation, rerun the setup script with `--persist-model <value>` and/or `--persist-effort <value>`.
- Without `--persist-*`, every other codex-kit component reads whatever is already in `config.toml` as its default — this command's normal (non-persist) run never writes anything.

If `--enable-review-gate` / `--disable-review-gate` was passed:
- **Confirm via `AskUserQuestion` before running the script with that flag.** This toggles a `Stop` hook that runs on every future turn's end in this workspace until disabled again — not a one-time or session-scoped effect. State plainly what the flag will do (enable: every turn-end runs a Codex-side review before the session may stop; on error, timeout (up to 9 minutes), or unparseable output the gate **blocks** the stop and tells you to run `/codex-kit:review --wait` manually — it only lets the stop through without review in two narrow cases: Codex isn't set up yet, or this is the re-continuation after the gate already blocked once (`stop_hook_active`); disable: turns that gate off entirely) before asking. **This confirmation is the review gate's own named exception to the session-level first-send gate** (`codex-prompt-protocol/references/shared-skill-conventions.md` §3): once enabled, the gate dispatches to Codex automatically on every future turn's end with no per-invocation confirmation possible in a hook context — this one-time, explicit opt-in confirmation is what stands in for it.
- Only after confirmation, rerun the setup script with the validated flag.

Output rules:
- Present the full setup report (all checks above, one per line) to the user.
- If Codex is installed but not authenticated, preserve the guidance to run `!codex login`.
- Never omit or soften the sandbox-mode line, even when it's a pass.
