# Testing History

Why this skill is tested through its hook scripts rather than LLM-judged evals, and the dated history of
its smoke-test runs. `SKILL.md`'s `## Testing & Validation` section carries the current summary and the
checklists; this file holds the detail moved out of it.

## Why evals don't cover this skill's behavior

`evals/strategic-compact/evals.json` exists, but doesn't exercise this skill's actual hook-driven
behavior. That is by design, not omission (fixed 2026-09-21: the section previously said the file didn't
exist at all, which contradicted the recorded-run sentence two sentences later; found by CodeRabbit's
automated PR review against PR #368).

This skill's behavior is hook-driven automation (6 Bash scripts and 3 shared Python hooks, all wired via
`hooks/hooks.json`), not model-invoked guidance that a `skill-tester` blind-comparison eval measures.
There's no "with skill vs. without skill" prompt-completion difference to compare, since the skill never
depends on the model reading and following its own body text to act; the hooks fire deterministically
regardless.

A `skill-tester` Quick Workflow run was performed anyway on 2026-09-21, at explicit user request, to
confirm the mismatch directly rather than by assertion. 6/6 assertions passed, with 0 of this skill's
declared scenarios actually exercised: 0/21 at the time, 0/18 since 2026-10-16, when three
context-mode-switch scenarios were removed (originally reported as 0/10; see `evals.json`'s own
`coverage_note` for the recount history). A second Quick Workflow run on 2026-11-20 (issue #461, at commit
`docs(context-kit): close R35 and R34 gaps`) again passed 6/6; it predates the
move of this history out of `SKILL.md`.

The meaningful test surface is the hook scripts' own input/output contracts, verified directly (stdin to
stdout and exit code, against realistic and adversarial JSON payloads) rather than via an LLM-judged
eval; see `hook-development/scripts/test-hook.sh`. The persisted `scripts/smoke_test.py` exercises
`ctx-compact-milestone-detector.sh`, `ctx-compact-skill-category-detector.sh`, `ctx-compact-stop-check.sh`
and `ctx-compact-session-init.sh` directly against this contract, and imports and cross-checks
`context-monitor.py`'s `get_session_dir()` implementation.

**Known gap (hook-reviewer, 2026-09-18):** `ctx-compact-track-and-suggest.sh` (the most complex script:
async, with cross-process locking), `ctx-compact-instructions.sh`, `ctx-pre-compact.py` and
`ctx-post-compact-restore.py` have no direct stdin/stdout contract test of their own yet, only incidental
coverage via shared helper functions and constant cross-checks. Tracked as an open item, not silently
claimed as covered.

## Smoke-test run history

Newest first.

- **2026-11-10, 55/55:** PR #694 review fixes. The tool-call-count fallback is published as 0% so it
  cannot open the shell hooks' gate, and a milestone no longer spawns a desktop notification (2 new
  checks).
- **53/53**, after the cross-model-review fixes: the first milestone of a session is no longer held back
  by the cooldown (1 more check); the shipped window is back to 200k; a phase alert seen while gated
  stays pending until the gate opens; and the monitor reuses the last usage value when it falls out of
  the scanned transcript tail (2 new checks). Also the `display_startup_banner` setting (2 new checks).
- **48/48**, after the settings file moved to `assets/`. Tool-call thresholds now default to 50/100/150
  and come from the settings files (4 new checks).
- **44/44**, after issue #690, fix 4: 3 new checks cover the milestone gate, single-channel delivery and
  the 30-minute cooldown.
- **41/41**, after fix 3: 5 new checks cover the real-context alert gate in
  `ctx-compact-track-and-suggest.sh` and the monitor's `pct-<hash>` handoff, including an alert that came
  due while gated firing once the gate opens. The learn nudge is now a single one at 65%.
- **36/36**, earlier the same day (issue #690): the 4 `ctx-compact-stop-check.sh` checks now assert a
  non-blocking `systemMessage` instead of `decision: block`, and 7 new `check_monitor_*` checks cover
  `context-monitor.py`'s real-token-usage estimate, sidechain skipping and window-size precedence.
- **2026-10-16, 29/29**, including `check_session_init_sweeps_expired_mode_files` for the mode-file
  sweep.
- **2026-09-21, 29/29**, before `check_session_init_resets_mode_file_on_startup` was removed with
  `detect_mode.py`. This run added:
  - `check_powershell_tool_payload_still_triggers_milestone`, for the Windows PowerShell-matcher fix;
  - 6 `check_skill_category_*` checks, for the new `heavy_operation`/`session_analysis` events;
  - `check_skill_category_unset_plugin_root_fails_open` and `check_session_init_resets_mode_file_on_startup`
    (removed 2026-10-16), for 2 fixes found by scripts-reviewer's own pass on this batch;
  - `check_no_hook_script_falls_back_to_cksum`, for a `cross-model-review` finding on the same batch;
  - from Codex's and CodeRabbit's automated PR reviews on PR #368,
    `check_skill_category_malformed_local_json_falls_back_to_defaults` and
    `check_stop_hook_delivers_multiple_queued_suggestions`, plus renaming the two
    `check_skill_category_*_start_and_finish` checks to `*_start` and rewriting
    `check_skill_category_priority_heavy_over_session_analysis` and
    `check_prefixed_content_with_hostile_tail_is_discarded` for the finish-phase removal and the
    pending-file queue rewrite respectively.
