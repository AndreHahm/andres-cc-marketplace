## Summary
3 of 5 `skill-tester` baseline-comparison dispatches for codex-kit's Phase 7 (Deep Test, Scoped) failed or returned malformed output — inconsistently, not as a clean architectural block, since 2 identically-shaped dispatches succeeded with real live-Codex results.

## Environment
- **Product/Service**: `codex-kit` plugin (this marketplace) — `plugin-lifecycle-downstream`'s Phase 7 (Deep Test), `skill-tester`'s baseline-comparison mode
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
1. Dispatch `Skill(skill-tester)` in full baseline-comparison mode for a given skill, via a forked agent (`subagent_type: "fork"`), against `evals/<skill>/evals.json` (repo root).
2. `skill-tester`'s Full Pipeline Phase 3 requires spawning 2 parallel sub-agents per eval (`with_skill` + `baseline`) via the `Agent` tool, for context isolation between the two runs.
3. For `codex-audit-loop` and `codex-peer-review`: this worked — both forks successfully dispatched their own sub-agents, made real live Codex CLI calls, and produced real `grading.json`/`benchmark.json` results on disk.
4. For `codex-rescue` and `codex-plan-loop`: the fork instead reported that the `Agent` tool was unavailable to it ("Fork is not available inside a forked worker" / "no other agent-dispatch path either") and refused to proceed, correctly avoiding a contaminated comparison rather than faking a result.
5. For `codex-windows-guardrails`: the fork returned a response entirely unrelated to its actual task (talking about "5 Phase 7 forks" and a "file-change note" as if it were the parent session, not running skill-tester at all).

## Expected Behavior
All 5 dispatches, being identically-shaped (same subagent_type, same Skill() call pattern, same tool needs), should either all succeed or all fail for the same, consistent reason.

## Actual Behavior
2 of 5 succeeded with real results; 2 of 5 failed with an `Agent`-tool-unavailable report; 1 of 5 returned malformed/off-topic output. The inconsistency itself is the finding — it suggests a race condition or non-deterministic constraint on fork-nested `Agent` tool availability, not a hard, documented limitation (nothing in this repo's own agent-dispatch documentation states forks categorically cannot use `Agent`).

## Error Details
~~~
codex-rescue / codex-plan-loop (representative):
"Blocked — cannot complete as directed. skill-tester's Full Pipeline (Phase 3)
requires dispatching 2 parallel agents per eval (with_skill + baseline) via the
Agent tool for true isolation between runs. As a nested fork, I have no Agent
tool access ('Fork is not available inside a forked worker' — and no other
agent-dispatch path either)."

codex-windows-guardrails (malformed):
"That file-change note reflects my own accumulated edits to the scope manifest
(Batch 1/2/3 summaries) — nothing external or unexpected. Continuing to wait
on the 5 Phase 7 forks."
~~~

## Impact
**Medium** — no data loss or security exposure, but a real coverage gap: 3 of codex-kit's skills (`codex-rescue`, `codex-plan-loop`, `codex-windows-guardrails`) still only have structural-only eval grading, not a live empirical `skill-tester` run, and the direct cause (fork/Agent-tool interaction flakiness) means a retry has no guaranteed better odds without understanding why 2 of 5 succeeded and 3 didn't. Each attempt (successful or not) costs roughly 780k-815k tokens, so blind retries are expensive.

## Additional Context
Found during a `plugin-lifecycle-downstream` full-pipeline QA run on `codex-kit` (2026-08-24), Phase 7 (Deep Test, Scoped — 5 skills touched by the run's own fixes). The user accepted partial Phase 7 coverage (the 2 successful results) rather than retrying the other 3, given the cost and the observed flakiness. Full context: `.claude/output/plugin-lifecycle-downstream/20260823T205538-codex-kit/scope.json`'s `phase7_deep_test` field, in that same run's worktree (gitignored, local to that session).

Suggested next step (not yet decided/prioritized): either retry the 3 failed skills via non-fork `Agent` dispatches (a fresh subagent, not a fork, to test whether fork-specific restriction is the actual cause) rather than another fork, or investigate directly whether forks have a documented/intentional restriction on nested `Agent` tool use that this repo's own fork-usage guidance doesn't currently mention.

Filed live: https://github.com/AndreHahm/andres-cc-marketplace/issues/110
