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

**Update (2026-10-12, retested on `codex-cli 0.162.1`, issue #545):** the failure still reproduces, but it changed shape again: `CreateProcessAsUserW` is gone from the output (an exit 0 with this failure was already seen under issue #78, so the exit code itself is not new). `codex exec --sandbox read-only` **exited 0**; stderr carried no `CreateProcessAsUserW` and instead showed (timestamped tracing-log `ERROR` lines, not `ERROR:`-prefixed ones):

```
Failed to create unified exec process: helper_unknown_error: setup refresh had errors
<ISO-8601 timestamp> ERROR codex_core::tools::router: error=exec_command failed: CreateProcess { message: "Rejected(\"Failed to create unified exec process: helper_unknown_error: setup refresh had errors\")" }
```

and Codex's final message was "`dir` could not run because process creation failed; no output line was produced." One run on one machine, plus a second live run through `/cdx-setup`'s probe (issue #549), so the wording is not shown to be stable. Because this run exited 0, the path that handles it is `codex-kit`'s `isTotalInspectionFailure` ("process creation failed" as the stated cause); `classifyNonZeroExit` also reads the timestamped `ERROR` lines, but only for a hypothetical non-zero variant. Both remain free-text heuristics tied to Codex's current wording.

**Root cause found (2026-11-04, issue #644):** before every sandboxed shell command, Codex on Windows runs `codex-windows-sandbox-setup.exe` ("setup refresh"), which opens every file of its runtime tree `%LOCALAPPDATA%\OpenAI\Codex\runtimes\cua_node\<hash>\` for an ACL update. A file held open by a running process fails with a sharing violation (`os error 32`), and one failed file fails the whole refresh, so no process can start. Each Codex session starts its own `node_repl.exe` from that tree at launch, so a session locks the file its own next command needs; the desktop app's `codex-computer-use-swift.exe` and parallel reviewer sessions add more locks. The symptom is intermittent (139 of 178 refreshes failed in one day's sandbox log). Linux has no refresh step. Disabling the browser, computer-use and app-tools plugins did not help; `windows.sandbox = "unelevated"` avoids the refresh but the sandbox shell then fails on the Store-package `pwsh.exe` ("Access denied"). Fully quitting the Codex desktop app makes a lone command pass; it does not fix parallel reviewers. No Codex-side flag was found.

Mitigation in this repository: the parity review (`run-codex-review`) probes the sandbox first, treats an envelope that names this failure as could-not-run, keeps completed reviewers' findings in the failure file, and on Windows falls back to `codex-windows-guardrails` (`danger-full-access`) for a reviewer whose sandbox the probe confirms is down, the way `cross-model-review` does. Because the failure is intermittent, a probe that passed on any one try made a flaky sandbox read as healthy while reviewers kept failing (issue #652). The probe is now down if any of its three tries fails, one failed probe keeps the sandbox down for the rest of the run (only a probe sets this, never a reviewer's own text), each probe is recorded in the result file's `provenance.sandbox_probe`, and the fallback's files are re-checked by content hash before every unsandboxed call. `codex-kit`'s `isTotalInspectionFailure` also reports `helper_unknown_error` and `setup refresh had errors` (not the generic `(os error 32)`), so a `cross-model-review` pass that read nothing is no longer a clean approve. Still open: the check is best effort (it does not cover the guardrails override, the instruction files or `~/.codex/config.toml`), `create-pr` step 4.5 still passes `--sandbox-down` after a `cross-model-review` fallback, which skips the probe, and the two failure-wording lists are kept in step by hand.
