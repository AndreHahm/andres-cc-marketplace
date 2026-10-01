# test-agent-trigger.sh crashes with JSONDecodeError in its semantic fallback

## Summary
`agent-development`'s `test-agent-trigger.sh` fails with a Python `JSONDecodeError` inside its semantic fallback, so the trigger-phrase battery that this repo's testing rule names for agents cannot run in this environment.

## Environment
- **Product/Service**: `plugin-devkit`, `plugins/plugin-devkit/skills/agent-development/scripts/test-agent-trigger.sh`
- **Region/Version**: repository state on 2026-10-02; the `claude` CLI is on `PATH`

## Reproduction Steps
1. Write a phrase file with `+` (should trigger) and `-` (should not trigger) lines, for example `+ review my skill` and `- run R1-R37 naming compliance on this component`.
2. Run `plugins/plugin-devkit/skills/agent-development/scripts/test-agent-trigger.sh plugins/plugin-devkit/agents/skill-reviewer.md <phrase-file>`.
3. Run it again against an unmodified copy of the same agent file taken from `HEAD`. It fails the same way.

## Expected Behavior
The script reports PASS/FAIL per phrase, or fails with a clear message when the model's reply cannot be used.

## Actual Behavior
A traceback ends in `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`, raised from `json.loads` inside `run_semantic_fallback`. That fallback shells out to `claude -p` (`subprocess.run` in the script's embedded Python). No per-phrase result is printed.

## Impact
**Medium** - The cheap, deterministic agent test named in `.claude/rules/require-tests-for-behavior-changes.md` cannot be used here, so agent description changes get no trigger test.

## Additional Context
- Cause not diagnosed: I did not run the fallback command by hand, so it is unknown whether the model reply is prose around the JSON, empty, or affected by the session it ran in.
- Likely fix direction: parse defensively, and report the raw reply when it is not JSON.
- Found while editing the `skill-reviewer` agent description in the `plugin-rulebook` refactor, where the battery could not be run as the required test.
