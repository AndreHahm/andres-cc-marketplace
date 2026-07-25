# Response: "I know the R13 line-count threshold might be outdated -- check it and fix it if so"

## 1. Mode: Single-Rule Mode

This is **Single-Rule Mode** (`find → update`), not Bulk Mode.

Reasoning: `self-upstream-plugin-devkit.md`'s Step 0 frames the choice as "Bulk sweep across a whole plugin/component, or a single already-known rule?" The user has named one specific, already-known rule — R13's line-count threshold — not asked for a sweep across a whole plugin or component. That is exactly the case the workflow file calls out for Single-Rule Mode ("a single already-known rule"), and it matches Testing & Validation scenario 4 ("self-upstream-plugin-devkit, single-rule mode") rather than scenario 3 (bulk). Because the target ("R13 line-count threshold") is already specified, Step 0's mode question can be treated as already resolved per its own exception clause — "unless `$ARGUMENTS` already specifies a mode and target" — so I would not re-ask which mode before proceeding; I'd state that Single-Rule Mode applies and proceed straight to Step 1.

## 2. Correct sequence of steps/commands

Per `workflows/self-upstream-plugin-devkit.md`'s Single-Rule Mode section:

1. **`Read('${CLAUDE_PLUGIN_ROOT}/commands/find-dev-rule.md')`**, then follow its documented Steps directly (commands aren't `Skill()`-invocable per `SKILL.md`'s "Slash Commands Are Not `Skill`-Invocable") against the query "R13 line-count threshold." This is read-only and presents a finding classified as one of `CONFIRMED` / `OUTDATED` / `MISSING` / `CONFLICT` / `NOT-OFFICIAL` / `UNVERIFIABLE`.
2. **If the finding is stale** (`OUTDATED`, `MISSING`, or `CONFLICT`): ask via `AskUserQuestion` — "Update R13 using the official-docs recommendation?" This is described as "a first, coarser gate" before the command's own internal confirmation.
   - If the finding comes back `CONFIRMED` (still accurate) instead, stop here and state plainly that nothing needed updating — per the Exit Criteria, that's a normal, valid outcome, not a failure.
3. **If yes**, `Read('${CLAUDE_PLUGIN_ROOT}/commands/update-dev-rule.md')`, then follow its Steps. It re-runs `find-dev-rule`'s Steps 1–3 internally and has its own built-in pre-flight confirmation before actually making changes. It produces a change report printed in chat only (per-file:line blocks) — no file is written, so no `📄 ... written:` link line applies here (Single-Rule Mode is the documented exception to that convention).

**Exit criteria:** either the change report exists (rule was stale and updated), or Step 1 found nothing stale and the workflow said so and stopped.

After the mode-specific sequence completes, the shared tail still applies (same for all 3 workflows):

4. **Document** — invoke `human-doc-reviewer` (via `Agent`) against the plugin's human-facing docs to check whether this rule change needs a doc update; "no update needed" is a valid outcome. Any approved doc fixes go through their own `AskUserQuestion` and are applied via direct `Edit`/`Write`.
5. **Commit** — state the exact file list and commit message, then stage and commit per repo convention (state the file list/message first; if the update was only partial, commit only what actually changed, state the reduced scope, and confirm before committing). Document's own doc-fix commit, if any, is a **separate** commit from this one.
6. **Handover (optional)** — ask via `AskUserQuestion` whether to run a downstream QA pass, only offered if something actually changed.

## 3. Confirmation gates

Within the R13-specific update sequence itself (Single-Rule Mode Steps 2–3), there are **2 distinct confirmation gates**, and the workflow file explicitly calls out that the skill must not skip or duplicate either one:

- **Gate A — the skill's own coarser gate (Step 2):** an `AskUserQuestion` prompt — "Update {rule} using the official-docs recommendation?" — asked by `plugin-lifecycle-maintenance` itself right after `find-dev-rule` reports a stale finding. Its purpose is the human-decision checkpoint this skill's Boundaries section requires ("never decides what to fix itself") — it decides *whether to proceed into `update-dev-rule` at all*.
- **Gate B — `update-dev-rule`'s own built-in pre-flight confirmation (inside Step 3):** a second, more detailed confirmation that `update-dev-rule.md` runs itself, immediately before it actually applies any change. Its purpose is the command's own last-chance, granular confirmation of the concrete edit it's about to make. `self-upstream-plugin-devkit.md` is explicit that this skill's Gate A is "a first, coarser gate" before this "second, detailed pre-flight confirmation," and that the skill must not skip or duplicate it.

Beyond this pair, two more `AskUserQuestion` gates exist further downstream in the shared tail but are not part of the R13 update decision itself: one inside the **Document** step (which doc fixes, if any, to apply) and one for the optional **Handover** offer at the very end. If the question is scoped strictly to "the sequence that checks and fixes R13," the answer is the 2 gates (A and B) above.
