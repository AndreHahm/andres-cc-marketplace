## Summary
plugin-lifecycle-upstream's Phase 7 agent check runs every auto-derived trigger phrase, which breaks the phase's own "bounded smoke check" contract

## Environment
- **Product/Service**: `plugin-devkit`: `plugin-lifecycle-upstream` Phase 7 (agent components), `agent-development/scripts/test-agent-trigger.sh`
- **Region/Version**: `main` as of 2026-11-17
- **Browser/OS**: N/A

## Reproduction Steps
1. Read `plugins/plugin-devkit/skills/plugin-lifecycle-upstream/workflows/design-a-plugin.md`, Phase 7, agent bullet: it calls `test-agent-trigger.sh <agent-file>` with no second argument (auto-derive mode).
2. Read the auto-derive branch of `test-agent-trigger.sh`: it writes every bullet of the agent's `## When to invoke` section (or every quoted phrase in its description) to the phrases file.
3. Read the per-phrase loop: each phrase starts a nested `claude -p` session, plus a semantic-fallback model call when that session does not delegate. Phase 7 may repeat the run up to 3 times against peer agents.
4. Compare with `plugin-lifecycle-upstream/SKILL.md` line 95 and line 284.

## Expected Behavior
Phase 7 matches its own contract. SKILL.md line 95: "Phase 7 is a bounded smoke check ... At most 3 checks run ... not that every declared trigger phrase fires correctly ... Exhaustive per-trigger-phrase testing ... [is] gated behind an explicit user decision (plugin-rulebook R26)". SKILL.md line 284: "Phase 7 never runs a component's full trigger-phrase battery".

## Actual Behavior
Every Phase 7 agent check runs the agent's full derived phrase list (typically 2-4 phrases), so one check makes several nested model calls, and up to 3 checks may run, all without the user decision R26 requires.

## Error Details
~~~
N/A: a contract mismatch, not a runtime error.
~~~

## Visual Evidence
N/A

## Impact
**Medium** - Phase 7 spends unapproved nested LLM calls in what is documented as a quick gate, and the skill's stated contract disagrees with its own workflow. No functional break.

## Additional Context
- Pre-existing: the script on `main` already ran every derived phrase. `design-a-plugin.md` described the call as using "a single representative phrase", which hid the mismatch. The #460 fix corrects that sentence, which made the conflict visible; both reviewers in that PR's cross-model review confirmed it (major, high confidence). It was left out of #460 by choice, to keep that PR scoped to the script and its wording.
- Options:
  1. Cap Phase 7 at one phrase, for example with a one-line temporary phrases file or a script option that limits auto-derive to one phrase. Note that the R26 backing hook (`pdk-r26-expensive-action-check.py`) treats a phrases-file argument as an expensive action, so its signature may need to change too.
  2. Relax the SKILL.md line 95 and line 284 contract, and add an explicit user gate before the per-phrase calls.
- Related: #460; #570 item 14 (auto-derive picks unsuitable lines as phrases).
