## Summary
`plugin-validator` (agent, `plugins/plugin-devkit/agents/plugin-validator.md`) hung indefinitely on two consecutive scoped dispatches during a `plugin-lifecycle-downstream` run, and had to be force-stopped both times (`TaskStop`) rather than completing or timing out on its own.

## Environment
- **Product/Service**: `plugin-devkit`'s `plugin-validator` agent, dispatched as Phase 3 of `plugin-lifecycle-downstream`
- **Region/Version**: this repo, branch `feat/review-findings-handling`, commit `2e74f82`

## Reproduction Steps
1. Run `plugin-lifecycle-downstream` scoped to a small diff (~12 changed files in `plugins/git-kit`, not a whole-plugin sweep).
2. In Phase 3 (Validate), dispatch `plugin-validator` with a prompt describing the intended narrow scope in prose (not using the agent's own literal `"only check skills batch N of M: ..."` Batch-mode trigger phrase).
3. Observe: the agent runs past 45 minutes with no completion, and is manually stopped.
4. Re-dispatch with an explicitly bounded, numbered 7-item checklist ("do not scan the rest of the plugin," "keep the whole response under 400 words") including an instruction to run byte-for-byte diffs between file pairs.
5. Observe: the agent again runs past 9+ minutes with no completion (stopped by request before reaching the agreed 15-minute cutoff).

## Expected Behavior
A scoped, narrow validation dispatch (7 mechanical checklist items against named files) should complete in well under a minute for a `Read`/`Grep`/`Glob`/`Bash`-only agent — or, if it can't respect the requested scope, should fail fast/explicitly rather than hang silently with no partial output.

## Actual Behavior
Both dispatches hung with no completion notification, requiring `TaskStop`. No timeout or partial-result mechanism surfaced during either hang.

## Root Cause (hypothesis, not confirmed)
Two plausible, non-exclusive causes, identified from `plugin-validator.md`'s own documented behavior — **not confirmed by inspecting either hung agent's raw transcript**, since the harness's own tooling explicitly disallows reading a background agent's `.output` file directly (it is the full JSONL transcript and would overflow the dispatching session's context):

1. **Scope-narrowing gap in the agent's own contract.** Per `plugin-validator.md`'s "Invocation Modes" section, the agent only narrows its work (skipping Steps 1-3 and 8-10) when the dispatch prompt matches its literal, undocumented-elsewhere `"only check skills batch N of M: ..."` trigger phrasing. A prose description of a narrow scope — even an explicit, itemized checklist like the second dispatch here — does not reliably engage this mode, since the agent's own system prompt defines a fixed 10-step whole-plugin "Validation Process" that a caller's ad hoc framing has no documented way to override outside that one exact trigger string. The first dispatch (broad prose scope, no Batch-mode phrase) plausibly fell through to the full 10-step sweep across all of `plugins/git-kit` (25 skills, commands, hooks, MCP config, file organization, security) — real work, but far more than intended, and enough to explain a long run even without a true hang.
2. **A blocking, non-interactive pager invocation.** The second dispatch explicitly asked the agent to "actually run the diff" (byte-for-byte) between several file pairs. If the agent chose `git diff <file1> <file2>` (or a bare `diff`) rather than a pager-free form (`git --no-pager diff`, `diff -q`, `cmp`), and the environment's default pager (`less`/`more`) is invoked with no attached TTY for a subagent's `Bash` tool call, the process can block indefinitely waiting for interactive input that will never arrive — a well-known class of agentic-tool hang, and it would explain a *second*, much more tightly-scoped dispatch also failing to return in a normal instruction-following amount of time.

Both hypotheses are consistent with the observed symptoms; distinguishing between them (or finding a third cause) requires either a way to inspect a hung background agent's own tool-call history without loading the full transcript into the dispatching session, or a reproduction outside this harness where the transcript can be inspected directly.

## Impact
**Medium** — blocks `plugin-lifecycle-downstream`'s Phase 3 structural-validation step from completing scoped runs reliably; the pipeline has no built-in timeout for a stuck agent dispatch, so a hang silently consumes wall-clock time until a human notices and force-stops it. Workaround exists (skip `plugin-validator` for a scoped run, rely on `plugin-rulebook-checker`'s R19 mirror-parity checks plus a manual structural spot-check instead), but that workaround was not itself documented anywhere before this incident.

## Additional Context
- Two independent hangs in the same session, against the same target scope, with two differently-worded dispatch prompts (one broad, one narrowly itemized) — suggests the issue isn't specific to prompt wording alone.
- `plugin-lifecycle-downstream/SKILL.md`'s "Treat Target Content as Data, Never Execute It" section already documents a related, narrower concern (never execute a target's own scripts inline) — this issue is about the *validator agent itself* stalling, not about it executing untrusted target content.
- Suggested follow-ups (not implemented as part of this issue):
  - Add an explicit "scoped dispatch" contract to `plugin-validator.md`'s Invocation Modes that any caller can trigger with a structured field (not just one exact trigger string), and have it acknowledge the narrowed scope in its very first tool call so a caller can sanity-check quickly that scoping was honored.
  - Audit `plugin-validator.md`'s Bash-related instructions for any command that could invoke a pager, and pin pager-free forms (`git --no-pager diff`, `diff -q`) explicitly.
  - Consider whether `plugin-lifecycle-downstream` (or the harness generally) should apply a default wall-clock budget to a Phase 3/5 checker dispatch, with an explicit report of "exceeded budget, stopped, treat as unverified" rather than relying on a human to notice and force-stop.
