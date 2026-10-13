# Exit-0 "process creation failed" Codex result for skill-reviewer (Windows, Codex 0.162.1)

Sources: `plugins/plugin-devkit/skills/plugin-auditor/references/codex-backend.md`, sections "Isolation: reactive, not proactive", "Windows-Guarded Execution Profile", "Codex Path" step 8 and "Adapter". Also `plugin-auditor/SKILL.md` Testing & Validation item 14.

## (a) Can the resolver record it as a clean review? No.

Relied on: "Isolation: reactive, not proactive".

- The bridge does not verify that `read-only` works. It passes the value through to a real `codex exec`, and on Windows that call fails to spawn any process.
- That failure is "**not** reliably a non-zero exit". On Codex 0.162.1 (issue #545), `codex exec` exited 0 and its final message said process creation failed.
- So an exit 0 with a schema-valid, zero-finding envelope is a total inspection failure, not a clean review. The zero findings mean nothing was inspected.
- SKILL.md item 14 says the same: it is "never recorded as a clean review".
- The "Adapter" table would otherwise fold `inspection_limits` into a coverage note and move on. That only applies to a real success. This shape must be caught earlier and treated as a typed failure.

## (b) What reclassifies it, and as what?

Relied on: "Isolation: reactive, not proactive".

- `codex-review-bridge` reclassifies it. Its zero-findings `isTotalInspectionFailure` heuristic matches the "process creation failed" phrasing.
- The typed failure is `isolation_profile_unavailable`. SKILL.md item 14 says "the bridge reclassifies it".
- The resolver (the plugin-auditor skill) does not do this. It only reacts to the typed failure the bridge returns.
- The heuristic is free-text and tied to Codex's current wording. It fires only while that wording stays recognized.

## (c) What the resolver does next with skill-reviewer

Relied on: "Codex Path" step 8, and "Windows-Guarded Execution Profile" ("When this profile is attempted").

- The default is a fallback. It is a typed failure, so skill-reviewer goes to the Claude-native `Agent()` dispatch.
- The category (`isolation_profile_unavailable`) is recorded once as a note on that dispatch's `coverage` entry. It is not stamped on individual findings.
- The exception is the Windows-guarded path, which is attempted only when both hold:
  - (i) the `read-only` attempt returned `isolation_profile_unavailable`, by either route; this case counts;
  - (ii) a `guarded-dispatch.mjs --dry-run true` call passes, meaning the guardrails opt-in is enabled.
- If the dry run returns any typed failure (`guardrails_disabled` included), skill-reviewer goes to Claude-native with no prompt.
- After a passing dry run, the resolver asks a second `AskUserQuestion` before the real call. It must state that the profile has no sandbox. The question is asked once per audit run, and the answer covers the remaining reviewers.
- A declined or unavailable prompt, or a denied permission prompt, means Claude-native.
- A failure on the guarded path folds back into step 8 and ends in Claude-native.
- By default (guardrails not enabled) none of the guarded path applies and the reactive fallback is used.
- Costs and preconditions:
  - The `read-only` attempt on 0.162.1 costs one full model turn, so each such dispatch spends one real subprocess attempt.
  - The First-Send Confirmation must already have fired this session.

## (d) How this differs from the older non-zero-exit shape

Relied on: "Isolation: reactive, not proactive".

- New shape, Codex 0.162.1:
  - `codex exec` exits 0 and returns a valid envelope with zero findings.
  - Detection is by `codex-review-bridge`'s `isTotalInspectionFailure` heuristic.
- Older shape:
  - `codex exec` exits non-zero.
  - It is classified by `codex-exec.mjs`'s non-zero-exit stderr classification as `isolation_profile_unavailable`, from `ERROR:` lines or from a tracing-log spawn error.
  - Older 0.146/0.147 shapes that do not match fail closed to `non_zero_exit`.
  - The exact patterns are in `codex-prompt-protocol/references/error-taxonomy.md`'s isolation row. I did not open that file; it is outside the permitted tree. The pointer comes from the section text.
- Both are free-text heuristics, and the section says the error wording changed between 0.146, 0.147 and 0.162.1.
