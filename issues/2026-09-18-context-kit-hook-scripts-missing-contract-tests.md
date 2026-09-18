## Summary
context-kit: 6 hook scripts lack direct stdin/stdout contract tests

## Environment
- **Product/Service**: context-kit plugin (this marketplace)
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
N/A — this is a test-coverage gap, not a reproducible bug. Found during
`plugin-lifecycle-downstream`'s Phase 11 (whole-plugin QA grading) on the `context-kit` plugin, by the
`hook-reviewer` agent.

## Expected Behavior
Every hook script wired in `plugins/context-kit/hooks/hooks.json` has a direct stdin → stdout/exit-code
regression test of its own — the same pattern `plugins/context-kit/skills/strategic-compact/scripts/
smoke_test.py` already applies to `compact-milestone-detector.sh` and `compact-stop-check.sh` (16 real
checks, exercised against realistic and adversarial JSON payloads), and `plugins/context-kit/skills/
context-mode/scripts/smoke_test.py` already applies to `detect_mode.py`.

## Actual Behavior
6 of 9 hook scripts wired in `plugins/context-kit/hooks/hooks.json` have no direct stdin/stdout
contract test — only incidental coverage via shared helper functions and constant cross-checks:

- `plugins/context-kit/hooks/scripts/compact-track-and-suggest.sh` (`PreToolUse`, async) — the most
  complex: cross-process locking, env-sourced numeric thresholds, phase-transition detection
- `plugins/context-kit/hooks/scripts/compact-session-init.sh` (`SessionStart`) — `source=startup/
  clear/compact` branching, stale-file cleanup
- `plugins/context-kit/hooks/scripts/compact-instructions.sh` (`PreCompact`) — captures active plan
  status before compaction
- `plugins/context-kit/scripts/context-monitor.py` (`PostToolUse`) — live context-window health
  estimation
- `plugins/context-kit/scripts/pre-compact.py` (`PreCompact`) — plan-state capture, symlink-containment
  checks
- `plugins/context-kit/scripts/post-compact-restore.py` (`SessionStart`, matcher `compact|resume`) —
  plan-state restore

**Suggested fix:** extend the persisted-test-suite pattern to these 6 scripts — happy path, negative/
no-trigger path, and at least one malformed/adversarial-input path each, mirroring
`plugins/context-kit/skills/strategic-compact/scripts/smoke_test.py`'s existing style.

## Error Details
~~~
N/A — no error output; this is a coverage gap, not a failure.
~~~

## Visual Evidence
N/A

## Impact
**Medium** — not a live defect (these scripts have already been through multiple prior hardening
rounds per their own inline comments: `security-reviewer`, CodeRabbit, Codex, `cross-model-review`),
but a real test-coverage gap on the plugin's most complex/highest-risk scripts, with no automated
regression guard if they're edited again.

## Additional Context
This gap is already disclosed in `plugins/context-kit/skills/strategic-compact/SKILL.md`'s own Testing
& Validation section as a known, tracked limitation — not silently hidden. This issue exists to track
the actual follow-up work; filing it (rather than writing the tests inline) was an explicit decision to
defer the test-writing to a follow-up pass rather than block the wave-4 QA PR on it.
