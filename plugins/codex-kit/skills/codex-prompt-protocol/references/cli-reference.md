# Codex CLI reference

This is internal engineering reference for codex-kit's own scripts (`scripts/lib/codex-exec.mjs`, `scripts/codex-companion.mjs`) — not a user-facing CLI tutorial; end users interact with codex-kit's own commands/skills, never raw `codex exec`.

## Model / effort

codex-kit never hardcodes a model name — every component reads `model`/`model_reasoning_effort` from the user's own `~/.codex/config.toml` by default, with per-call `--model`/`--effort` overrides where a component exposes them. Do not add a hardcoded model list here; Codex CLI owns that list and it changes over time.

## Sandbox / automation flags

- `--sandbox read-only` / `--sandbox workspace-write` / `--sandbox danger-full-access` — always pass explicitly (never omit and rely on a default). codex-kit's own rule: any fallback to `danger-full-access` must be reported to the user explicitly, never silently.
- `--skip-git-repo-check` — bypass the git-repo requirement; only use after explicit user confirmation, since it has security implications the user should be aware of.

## The stdin-hang gotcha

Codex CLI reads stdin whenever stdin is non-TTY. In a subprocess/script context, if stdin is left open with nothing written to it, `codex exec` hangs indefinitely waiting for input that will never arrive. Two safe patterns:
- Non-piped calls: redirect `< /dev/null` explicitly.
- Piped calls: the upstream command must close its end (e.g. `cat file | codex exec ...` — `cat` naturally sends EOF).

`scripts/lib/codex-exec.mjs`'s `runCodexExec` avoids this a third way: it always writes an explicit prompt via `child.stdin.write(prompt); child.stdin.end();` — the `.end()` call closes stdin deterministically regardless of platform, without needing a shell-level redirect (the primitive uses `spawn`, not a shell).

## Timeout and crash recovery

- `codex exec` calls should always carry an explicit, bounded timeout — `scripts/lib/codex-exec.mjs` takes `timeoutMs` as a required-in-spirit parameter (defaults to 240000ms) and kills the process with `SIGTERM` on expiry, returning a `timeout` typed failure rather than hanging the caller.
- A **timeout** is not a **crash**: a timed-out call may have a resumable session; a crashed call (non-zero exit, no output) generally should not be blindly retried without understanding why it crashed first — surface the `detail` field to the user rather than silently re-running.
- Session-ID capture for resume: Codex reports its session/thread ID in stderr chrome as a run starts, not in the final-message file. Components needing resume (e.g. `codex-rescue`'s `--resume-last`) rely on the companion script's own job-tracking (`scripts/lib/tracked-jobs.mjs`, `scripts/lib/state.mjs`) rather than re-deriving this from raw CLI output.

## `--output-schema` / `--output-last-message`

The pattern the shared `runCodexExec` primitive (`scripts/lib/codex-exec.mjs`) builds on: `codex exec --output-schema <schema-file> --output-last-message <output-file>` constrains the final response to JSON matching the supplied schema and writes it to a file rather than relying on parsing stdout (which also carries progress/transcript noise). Every object in a schema passed this way should set `additionalProperties: false` to avoid the model padding its response with unrequested fields.
