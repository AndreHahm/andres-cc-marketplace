## Summary
On Windows, Codex's sandbox setup fails against the session's own `node_repl.exe`, so the local parity review cannot complete, and the repo's failure detection misses it in both directions (false could-not-run, false clean)

## Environment
- **Product/Service**: `scripts/marketplace_ci/review.py` (`run-codex-review`), `git-codex-parity-review.py`, `codex-review-bridge/scripts/bridge-invoke.mjs`, `cross-model-review`
- **Region/Version**: Codex CLI 0.162.1 (CI pins 0.147.0), `[windows] sandbox = "elevated"` in `~/.codex/config.toml`
- **Browser/OS**: Windows 11, native (no WSL), Git Bash and PowerShell. Verified live on 2026-11-04.

## Reproduction Steps
1. On Windows with the Codex desktop app installed, run `uv run python .claude/scripts/git-codex-parity-review.py --output <fresh file in a scratch dir>` on a branch with a diff.
2. Observe exit 2 and `helper_unknown_error: setup refresh had errors` in the reviewers' failure details.
3. Run `codex exec --sandbox read-only -C <empty dir> "run: type hello.txt"` and observe the same error instead of the file content.
4. Compare with `cross-model-review` on the same diff: it returns verdicts, with a note that the shell helper failed.

## Expected Behavior
All five parity reviewers run and return findings, or the run says clearly which reviewers did not inspect anything. A reviewer that could not read a single file is never reported as clean.

## Actual Behavior
- The parity review ended exit 2 in four runs. A different set of 2-3 of the 5 reviewers could not run each time. When any reviewer fails, the result file drops all findings: `scripts-reviewer` reported status `findings` in two runs and the details were lost.
- `cross-model-review`'s Codex passes hit the same shell failure, but still returned verdicts because that skill embeds the whole diff (about 35 KB) in the prompt. The parity reviewers get no embedded diff and must read files with shell tools.
- The detection is free-text matching in two places and is wrong in both directions. `isTotalInspectionFailure()` (a regex over `inspection_limits` of a zero-finding envelope) flagged none of four `cross-model-review` envelopes with notes like "helper could not initialize", "failed during environment setup" and "could not be started because the helper intermittently failed during process setup". `_inspected_nothing()` in `review.py` only treats a verdict starting with "inconclusive" as an empty review. A solo `scripts-reviewer` envelope (verdict "Unable to complete the static script review ...", 0 findings, note "failed before execution with `CreateProcess ... helper_unknown_error`") matched neither, so it would count as a completed clean review.

## Root cause
1. Before every sandboxed shell command, Codex runs `codex-windows-sandbox-setup.exe` ("setup refresh"). It opens every file of the runtime tree `%LOCALAPPDATA%\OpenAI\Codex\runtimes\cua_node\<hash>\` for an ACL update.
2. A file held open by a running process fails with a sharing violation (`os error 32`, "used by another process"). One failed file fails the whole refresh (exit 1), so no process can start.
3. Each Codex session starts its own `node_repl.exe` from that tree at launch (observed as a child of `codex.exe`, before its first shell command), so a session locks the file its own next command needs. The desktop app's `codex-computer-use-swift.exe` and its DLLs add locks (the app respawns it at once when killed). Parallel reviewer sessions add more.

Evidence:
- The sandbox log in `~/.codex/.sandbox` showed 139 of 178 setup refreshes failed that day, always `os error 32` on `node_repl.exe` or a Computer Use DLL.
- A write-open probe fails on exactly those running files and succeeds on `node_repl.exe` when it is not running.
- `codex sandbox cmd /c echo ok` failed 3 of 3 with the helper running and passed 2 of 2 after the desktop app was fully quit.
- Disabling the browser, computer-use and app-tools plugins, `notify`, and the `browser_use`/`computer_use`/`in_app_browser` features did not help.
- `windows.sandbox="unelevated"` avoids the refresh, but the sandbox shell then resolves to the Store-package `pwsh.exe` under `WindowsApps`, which a restricted token cannot run ("Access denied"). With `WindowsApps` removed from `PATH`, a single read-only `codex exec` worked, but in the full parity run it only reduced the failures.
- Linux has no such refresh step.

## Error Details
~~~
Failed to create unified exec process: helper_unknown_error: setup refresh had errors
runtime read/execute validation failed: validate runtime read/execute access on
  %LOCALAPPDATA%\OpenAI\Codex\runtimes\cua_node\<hash>\bin\node_repl.exe:
  open ACL target for root-only update: ... used by another process. (os error 32)
~~~

## The guardrails fallback
- The parity review does not use `codex-windows-guardrails`: `review.py` has zero references to `guarded-dispatch`, and `isolation_profile_unavailable` just becomes a failed reviewer. The fallback is wired only into `cross-model-review` resolver step 2, `plugin-auditor`'s Codex backend and some codex-kit commands.
- In `cross-model-review` it never fired either, because none of the four broken runs returned `isolation_profile_unavailable`.
- Its `SKILL.md` lists a live `danger-full-access` run as an open item. First live run recorded: `guarded-dispatch.mjs` with the existing local override enabled and one tiny probe instruction exited 0 with a valid envelope, and Codex's shell ran and returned the real first line of a repo file (`execution_profile: danger-full-access`).

## Impact
**High** - On Windows the local pre-PR parity gate cannot complete, and its output is unreliable in both directions. It blocks the PR flow for Windows contributors and for any change to `review.py`. The workaround (fully quit the Codex desktop app) only helps a lone command.

## Additional Context
Fix options, not decided:
- **A.** Wire `guarded-dispatch` into the parity dispatch as a retry for `isolation_profile_unavailable`, only with explicit user consent (unsandboxed, full account access, network).
- **B.** Detect the failure robustly instead of by free text: a pre-flight sandbox probe before dispatch; treat any reviewer whose envelope reports a tool failure, or whose `inspection_limits` mention `helper_unknown_error` / `setup refresh`, as could-not-run; keep findings in the result file when some reviewers fail.
- **C.** Avoid the root cause: do not start `node_repl.exe` in review sessions, or exclude the runtime tree from the refresh. This needs a Codex-side change; no flag was found.
- **D.** Update `plugins/plugin-devkit/KNOWN_ISSUES.md` (it records the symptom as unexplained) and the guardrails `SKILL.md` open item.

Related: #163 (the opposite classifier weakness, a false positive), #545 and #549 (the symptom, closed), #568 (umbrella refactor of the review path), #623 (where this was found). A separate Windows CRLF bug in the parity `.paths` file that hid this earlier was fixed in commit 6bfad8d3.

Suggested priority: `p: high`.
