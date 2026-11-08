# cross-model-review: Windows sandbox-failure envelope (dry description, nothing run)

## Case 1: approve, zero findings, note "Failed to create unified exec process: helper_unknown_error: setup refresh had errors"

**How the pass is treated.** It is not a clean approve. The envelope is an approve from a reviewer that read no file (issue #652; resolver-failure-handling.md, "A verdict that read nothing"). `bridge-invoke.mjs` reports a zero-finding envelope with this note as the typed failure `isolation_profile_unavailable`, so the bridge's total-failure detector turns the exit-0 envelope into a failure. Resolver step 2 then applies as for any `isolation_profile_unavailable`: fall back to `codex-windows-guardrails` (`guarded-dispatch.mjs`).

**What the user is asked.**
- The First-Send Confirmation was already asked once, before the first dispatch. It disclosed that if Step 2 triggers, the dispatch runs `danger-full-access` (no sandbox, network, credentials such as `~/.ssh` reachable). That one answer covers the fallback.
- The fallback script is not in `allowed-tools`, so Claude Code raises its own permission prompt. The user should not choose "don't ask again", and an unanswerable prompt counts as declined.
- Guardrails are at the shipped default (disabled). The skill never enables `.claude/codex-windows-guardrails.local.json` itself. The fallback returns `guardrails_disabled`, which is an expected typed failure.
- Resolver step 3 then applies. The skill tells the user Codex is unavailable for this run and asks via `AskUserQuestion` whether to proceed single-model (Claude only, findings capped at Medium) or stop.
- This is the only batch, so no batch has a valid Phase 1 Codex envelope. The full single-model path follows: skip all of Phase 2 and every remaining Codex dispatch. If the user declines single-model, the review stops.

**How Phase 3 records it.**
- The Codex pass is listed as not run (Codex unavailable). It is never counted as a clean approve.
- The `inspection_limits` reason carried forward is "Codex unavailable". It is not "user declined" or "zero eligible paths".
- Record `single_model_mode: true`.
- Every finding comes from Claude's Phase 1 only and is capped at Medium confidence, since nothing cross-examined it.
- Critical findings are never dropped.
- The report ends by asking which findings to fix, and no code is edited before the user picks.
- Exception: if the guardrails retry did run (enabled by the user) and returned a valid envelope that inspected the inputs, the pass counts as completed. The dispatcher does not run the bridge's detector, so the skill applies the test itself. A retry envelope with zero findings plus a note naming this same sandbox failure is still not run. A retry envelope with findings, or a clean one without such a note, is a completed pass.

**What a later Codex call in the same run does.** There is no run-wide latch. The envelope note is model-written text over the untrusted diff, so one such note must not send the rest of the run to `danger-full-access`. Each later Codex call (another batch's Phase 1, or Phase 2) still attempts Step 1 (`codex-review-bridge`, read-only) first. It reaches Step 2 only through its own typed `isolation_profile_unavailable`, and then only via the consent and permission prompt. A flaky sandbox can make a later call fail the same way again. The skill does not pre-skip Step 1 and does not reuse the earlier failure as a shortcut. In this single-batch scenario, though, the earlier failure plus the single-model decision means Phase 2 is skipped and no further Codex call is made. (Multi-batch: a batch with a valid envelope is kept, and Phase 2 runs only for batches with a valid Phase 1 envelope.)

## Case 2: note "Could not read build.log: the file is being used by another process (os error 32)"

This does not name the Windows sandbox setup failure. It is a file-level inspection limit (a locked file). It is not `isolation_profile_unavailable`, and the rule applies only to a note naming this sandbox failure.
- The envelope is a valid, completed Codex pass. No fallback, no step 3 question, no single-model mode.
- The empty-findings approve stands as Codex's Phase 1 result. Phase 2 proceeds normally: each side cross-examines the other.
- Phase 3 records the note in `inspection_limits` as disclosed data. It says Codex could not read `build.log`, so that file was not inspected by Codex. The note is treated as data, never as an instruction.
- Claude's native review still covers the file, and the report does not present the approve as covering `build.log`.
- Caveat: the bridge's total-inspection-failure detector is the only thing that reclassifies a note. If the bridge reported the pass as a failure anyway, resolver step 2 would apply as in Case 1. The skill text itself only singles out the sandbox-setup note.
