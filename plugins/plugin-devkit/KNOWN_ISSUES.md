# Known Issues

Git-tracked record of external-tool issues discovered while working on `plugin-devkit`, kept durable (unlike `.draft/`, which is gitignored) so a finding isn't lost the moment the session that found it ends.

## Codex CLI: sandboxed execution fails on Windows (found 2026-08-06)

**Component/tool:** `codex` CLI (`@openai/codex`, tested at `codex-cli 0.146.0`), not a `plugin-devkit` component itself. Recorded here because it directly blocks the design in `.draft/_open/plugin-devkit/codex-integration/` (gitignored — that directory has the full concept and verification detail; this entry is the durable summary).

**Symptom:** on Windows (tested: Windows 11), `codex exec` fails every command execution attempt when run with either `--sandbox read-only` or `--sandbox workspace-write` (including the default when no `--sandbox` flag is given). The model successfully starts, but every attempt to actually run a shell command (needed for it to read a file, which is the minimum a review/inspection task requires) errors:

```
ERROR codex_core::exec: exec error: windows sandbox: runner failed during SpawnChild:
CreateProcessAsUserW failed: 1920 (Das System kann auf die Datei nicht zugreifen.)
```

**Confirmed NOT a config issue:** this machine's `~/.codex/config.toml` already sets `[windows] sandbox = "elevated"` — that setting does not fix the failure, so it governs something else (likely a UAC-elevation prompt), not this spawn error.

**Only working sandbox mode found:** `--sandbox danger-full-access` — which removes all sandboxing (unrestricted write/execute access), defeating the purpose of running a read-only review task through Codex in the first place.

**Impact:** any design that relies on running Codex CLI non-interactively with a safe (read-only or workspace-write) sandbox on Windows is currently blocked. `danger-full-access` is the only mode that lets Codex actually execute commands on this platform as of the tested version.

**Status:** unresolved. Not yet filed against the upstream `codex` CLI project. Options going forward: (a) file an upstream bug report once a minimal reproduction is isolated, (b) re-test against a newer Codex CLI release to see if this has since been fixed, (c) accept `danger-full-access` for a specific use case with an explicit, disclosed compensating control (e.g. running only inside an already-isolated CI/container environment).

**Also verified while investigating this (working correctly, not blocked):**
- `codex exec`'s non-interactive invocation syntax, and its `--output-schema`/`--output-last-message` structured-output mechanism, both work as documented — confirmed via a live test producing schema-conformant JSON findings against a real file in this repo.
- The JSON Schema passed to `--output-schema` must set `additionalProperties: false` on every nested object level, not just the schema root — omitting it on a nested object fails with `Invalid schema for response_format 'codex_output_schema'`, a constraint not mentioned in `codex exec --help`.

**Update (2026-08-15, retested on `codex-cli 0.147.0`):** the failure still reproduces on this platform, but the specific error changed from the `0.146.0` finding above. `--sandbox read-only` now fails with:

```
ERROR codex_core::exec: exec error: windows sandbox: runner failed during SpawnChild:
CreateProcessAsUserW failed: 5 (Zugriff verweigert)
```

Windows error 5 is `ERROR_ACCESS_DENIED`. This is more specific than the original `1920` ("system cannot access the file specified") and is consistent with — though not proof of — a privilege-elevation requirement: `CreateProcessAsUserW` normally requires the *calling* process to hold `SeAssignPrimaryTokenPrivilege`/`SeIncreaseQuotaPrivilege`, which a standard (non-elevated) user token does not carry by default. This session ran as a confirmed non-elevated user (`[Security.Principal.WindowsPrincipal]::IsInRole(Administrator)` returned `False`) when the error occurred.

**Not established:** whether the sandbox actually succeeds when the calling process *is* elevated. That test wasn't performed — it requires an interactive UAC elevation this investigation didn't attempt — so treat "Windows Codex sandboxing is effectively admin-gated" as a plausible, evidence-consistent hypothesis, not a confirmed fact. What *is* now confirmed across two separate CLI versions (`0.146.0` and `0.147.0`) is the practical bottom line: no sandboxed mode has worked on this platform either time, and `danger-full-access` remains the only mode that lets Codex execute anything locally here.

**Update (2026-08-15):** option (c) above (accept `danger-full-access` with an explicit, disclosed compensating control) has since been implemented for one specific caller: `codex-kit`'s `codex-windows-guardrails` skill provides best-effort pre-flight guardrails (repository-boundary, secret-file, and instruction-containment checks, plus an instructed but not enforced dangerous-command allowlist) so `plugin-auditor`'s optional Codex backend can attempt `danger-full-access` locally on Windows. It is explicitly *not* a real sandbox — see that skill's own SKILL.md for the exact boundary of what it does and doesn't guard against. Disabled by default; this doesn't resolve the underlying `codex` CLI issue, only mitigates its impact for that one opted-in caller.
