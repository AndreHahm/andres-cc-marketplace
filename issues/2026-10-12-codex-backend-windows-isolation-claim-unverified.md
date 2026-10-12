## Summary
`plugin-auditor`'s `codex-backend.md` claims a real Windows sandbox failure is classified as `isolation_profile_unavailable`. The #544 classifier change narrowed that classification, and no real Windows Codex stderr was ever captured to confirm the claim still holds.

## Environment
- **Product/Service**: `plugin-devkit` (`plugins/plugin-devkit/skills/plugin-auditor/references/codex-backend.md`), `codex-kit` (`plugins/codex-kit/scripts/lib/codex-exec.mjs`)
- **Region/Version**: `main` plus the #544 fix (commits `4db102e9` and `d034a4b1` on `fix/codex-exec-misclassified-exit`); Codex CLI 0.162.1 observed on Linux
- **Browser/OS**: Windows (the affected platform); the evidence gap exists because it cannot be captured on Linux

## Reproduction Steps
1. On Windows, run a read-only `codex exec` (for example through `codex-review-bridge` with `--execution-profile read-only`) on a machine where Codex's sandbox cannot start a process.
2. Capture the full stderr of the failing run.
3. Pass that stderr through `classifyNonZeroExit` in `plugins/codex-kit/scripts/lib/codex-exec.mjs`.

## Expected Behavior
The result is `isolation_profile_unavailable`, so `cross-model-review`'s documented Step 2 fallback triggers, as `codex-backend.md` (around lines 117-119) says it does.

## Actual Behavior
Unknown. The claim was true while the classifier tested the whole stderr for the bare word "sandbox". Since the #544 fix it classifies on Codex's own unindented `ERROR:` lines (taken from the whole stderr) and anchors the isolation pattern on concrete shapes (`CreateProcessAsUserW`, `bwrap`, `landlock`, `seccomp`, "sandbox failed/error/denied/unavailable"). A started Codex session that prints no `ERROR:` line, and any long stderr without one, falls through to `non_zero_exit`; only a short banner-less stderr (a failure before the session starts) is read whole. If real Windows Codex prints the `CreateProcessAsUserW` failure on a non-`ERROR:` line, it is now reported as `non_zero_exit`, and the fallback does not trigger automatically.

## Error Details
~~~
Evidence gap: the CreateProcessAsUserW fixtures in
plugins/codex-kit/scripts/smoke-tests/codex-exec-isolation-classification.mjs are synthetic
(the file's header says so). The only real captured Codex stderr is Linux, Codex 0.162.1,
for an unservable model.
~~~

## Visual Evidence
None.

## Impact
**Low** - Fails closed: a missed isolation failure becomes `non_zero_exit`, and `cross-model-review` then asks the user to go single-model or stop. It cannot widen privilege. It costs availability, and only on Windows with the `codex-windows-guardrails` opt-in enabled.

## Additional Context
Found by the `security-reviewer` pass on the #544 fix (finding m2).

Needed, either of:
- capture real Windows stderr for a failing read-only sandbox, add it as a fixture to the smoke test, and confirm the classification; or
- soften the "correctly reports this as `isolation_profile_unavailable`" sentence in `codex-backend.md` until that evidence exists.

Related: #544 (the classifier fix), #78 (closed, Windows dispatch), #163 (a different false-positive path in `isTotalInspectionFailure`, the zero-exit Windows case).
