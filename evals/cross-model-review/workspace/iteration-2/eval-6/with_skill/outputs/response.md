# Where this matters in Preflight, and what happens downstream

## The scenario

The diff about to become a PR modifies `plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs` — one of the two dispatcher scripts `cross-model-review` itself invokes to run Codex — alongside unrelated application code changes. Nothing about the unrelated application-code portion of the diff matters to this analysis; the relevant fact is purely that one specific path in the changed-file list matches a specific pattern.

## Where it's caught: Preflight step 6

Preflight step 5 already handles a related but distinct risk: it materializes the two trusted *prompt* files (`review.md`, `refute.md`) from `$BASE` via `git show`, specifically so that a diff under review can't rewrite the instructions that judge it. But step 5's own text is explicit that this protection is scoped to those two prompt files and does **not** extend to the *executable* dispatcher scripts:

> "Step 5 protects the two *prompt* files against a self-modifying diff; it does nothing for the *executable* — `bridge-invoke.mjs`/`guarded-dispatch.mjs` are run from the working tree by a repo-relative path with no `$BASE` verification of their own."

That gap is exactly what Preflight step 6 exists to catch. Step 6 greps the Preflight step 2 changed-file list (`git diff --name-only "$BASE...HEAD"`) for the pattern `plugins/codex-kit/.*/scripts/.*`. In this scenario, `plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs` is in that changed-file list and matches the pattern, so step 6 fires.

Note this check is purely path-based against the changed-file list already computed in step 2 — it doesn't care how large or how "unrelated" the rest of the diff is, or whether the application-code changes touch anything sensitive. A single matching path is sufficient to trip it.

(Separately, step 2's own charset/existence validation — `^[A-Za-z0-9._/-]+$`, plus `codex-windows-guardrails`' additional on-disk-existence check — is satisfied by this path, so `bridge-invoke.mjs` isn't excluded from Codex's `--target-paths`; it's still sent to Codex as one of the files to review, on top of triggering the step 6 disclosure.)

Per step 6, once the match is found, two things must happen, neither silent:

1. **Disclose it explicitly at the First-Send Confirmation** (not just proceed quietly).
2. **Record it in Phase 3's `inspection_limits`** that the Codex dispatcher itself was not trust-boundary-verified against `$BASE` for this run.

## What happens at the First-Send Confirmation

The First-Send Confirmation is the mandatory, once-per-session `AskUserQuestion` gate that fires before the *first* real Codex dispatch is attempted (regardless of which resolver path — sandboxed `codex-review-bridge` or the `danger-full-access` `codex-windows-guardrails` fallback — ends up being used). Per the skill's own text, it must state plainly:

- (a) the dispatched process can read anything under the repo root regardless of `--target-paths` — target paths only scope focus/what findings are checked against;
- (b) if the resolver ends up falling back to Step 2, the dispatch runs fully unsandboxed (`danger-full-access`), not the `read-only` profile Step 1 uses; and
- **(c) — the clause this scenario triggers** — because Preflight step 6 found the diff touching the Codex dispatcher scripts themselves, say so explicitly: the dispatcher about to run was not trust-boundary-verified against `$BASE` this run.

So in this scenario, the First-Send Confirmation's `AskUserQuestion` will explicitly call out that `bridge-invoke.mjs` — the very script about to be executed to dispatch Codex — is part of the changed diff and hasn't been checked against `$BASE`. There's a pointed irony here: if the resolver takes the Step 1 (sandboxed) path, the skill would be running the modified `bridge-invoke.mjs` from the working tree to review a diff that includes modifications to `bridge-invoke.mjs` itself — the exact self-modifying-tool risk step 5 was built to prevent for the prompt files, left structurally open for the executable.

The confirmation still offers the same two options as always — "Send to Codex for this run" / "Stay Claude-native for this run" — but now with the dispatcher-trust caveat folded into the disclosure the user sees before choosing. This fires before the backend is resolved, so it covers both the Step 1 and Step 2 outcomes, not just whichever one turns out to run.

## Downstream effect on the report

Whatever the user chooses, if Codex does get dispatched, Phase 3's synthesis step carries the disclosure forward: the final report's `inspection_limits` section records that the Codex dispatcher itself wasn't trust-boundary-verified against `$BASE` for this run, alongside any other inspection limits (charset/deleted-path exclusions from step 2, unverified-instructions fallback from step 5). This is additive to — not a replacement for — the actual review findings on the unrelated application-code changes, which proceed through Phases 1–2 normally.
