# Walkthrough: cross-model-review on local Windows, bridge fails, guardrails disabled

Scenario given: codex-kit is installed, `codex` CLI is on PATH, but `codex-review-bridge` dispatch
fails with `isolation_profile_unavailable` (the sandboxed `read-only` profile doesn't work on this
platform), and `codex-windows-guardrails` is still at its shipped default — disabled, with no
`.claude/codex-windows-guardrails.local.json` override present.

I am not invoking any command below — this is a description of exactly what the skill's own
instructions have me do, in order, once this failure occurs.

## Where this happens

Preflight (building `"${DIFF[@]}"`, computing the changed-file list, creating `$RUN`, resolving
`REPO_ROOT`, and materializing `$RUN/review.md`/`$RUN/refute.md` from `$BASE`) has already completed
without needing Codex at all — none of that touches the resolver. Claude's own native Phase 1 pass
(`$RUN/claude_fresh_eyes.json`) also doesn't need Codex. The failure described here happens the
first time the skill actually needs to reach Codex: Phase 1's Codex pass (or, if this is the first
Codex call of the session, whichever Phase 1/Phase 2 Codex dispatch comes first).

## Step 1 — First-Send Confirmation (fires once per session, before the first real Codex dispatch)

Before attempting *any* Codex dispatch — before the resolver's Step 1 is even attempted, so before
we know which backend will actually end up serving the call — the skill requires a mandatory
`AskUserQuestion`. I state:

- the reviewer persona about to be sent (e.g. `fresh-eyes-reviewer`) and the target paths (the
  changed-file list) about to be sent to Codex,
- (a) the dispatched process can read anything under the repository root regardless of
  `--target-paths` — that flag only scopes what it's *asked to focus on* and what its findings are
  checked against, not what it's technically able to see,
- (b) if the fallback (Step 2) ends up triggering, the dispatch runs `danger-full-access` — no
  sandbox at all, read *and* write/execute — not the `read-only` profile Step 1 uses.

I ask this before resolving the backend specifically because that's the only way the confirmation
covers both possible outcomes (sandboxed success, or the no-sandbox fallback) rather than only the
happy path. Options presented: "Send to Codex for this run" / "Stay Claude-native for this run".

Since the scenario stipulates the dispatch is actually attempted and hits `isolation_profile_unavailable`,
I take the user's answer here as "Send to Codex for this run" and proceed to the resolver.

## Step 2 — Resolver Step 1: attempt `codex-review-bridge`

I invoke `bridge-invoke.mjs` with `CODEX_KIT_REVIEW_REPO_ROOT="$REPO_ROOT"` exported,
`--execution-profile read-only`, the persona's instruction file, `--target-paths`, a fresh
`--dispatch-id`, and `--cwd "$REPO_ROOT"` — never a `--repo-root` flag on this script, since the
skill explicitly warns that flag is silently discarded by the bridge and would leave the process's
working directory/containment root pointed at wherever the skill happens to be running from instead
of the actual repo root.

## Step 3 — Bridge returns `isolation_profile_unavailable`

Per the resolver's own instructions, this is the expected, named failure mode "on local Windows —
`read-only`/`workspace-write` sandboxes are confirmed non-functional there." This is not treated as
a stop condition by itself — it's the documented trigger to fall back to Step 2.

## Step 4 — Resolver Step 2: attempt `codex-windows-guardrails`

I invoke `guarded-dispatch.mjs` with the same persona/instruction-file/target-paths, a
`--dispatch-id`, and `--repo-root "$REPO_ROOT"` (this script's own flag name, deliberately different
from Step 1's `--cwd`/env-var shape — the skill is explicit that the two scripts take different
flags and must never share one invocation shape). This is the `danger-full-access`, no-sandbox path
the First-Send Confirmation already warned about.

## Step 5 — Guardrails returns `guardrails_disabled`

Given the stated environment — `codex-windows-guardrails` shipped disabled by default and no
`.claude/codex-windows-guardrails.local.json` override exists — this attempt fails with a
`guardrails_disabled` typed failure. The skill is explicit that this is "expected, not a bug," and
just as explicit that **I do not enable this override myself**: the skill's own framing statement
("`Write` is scoped in practice to `$RUN`... never to `.claude/codex-windows-guardrails.local.json`
in particular — this skill never enables that override on the user's behalf") and the "Deliberately
NOT done" section ("No enabling `codex-windows-guardrails` on the user's behalf — it stays opt-in")
both rule this out. I do not create, edit, or suggest silently creating that file to work around the
disabled state.

## Step 6 — Resolver Step 3: degrade, don't retry

`guardrails_disabled` is explicitly named in the resolver's Step 3 list ("On any other typed failure
from either path — including `guardrails_disabled`...") as one of the failure types that ends the
attempt/fallback sequence rather than triggering any further retry. Per the resolver, having now
exhausted "attempt once, fall back once," I:

- tell the user Codex is unavailable for this run, and
- ask via a second `AskUserQuestion` whether to proceed single-model (Claude only — explicitly
  losing the cross-vendor benefit, with findings defaulting to Medium confidence since nothing
  cross-examines them) or stop the skill run entirely.

I do not re-attempt Step 1 or Step 2 again, and I do not silently continue without asking.

## Step 7 — Act on the user's choice

- **If the user chooses to stop:** the skill run ends here. I report that Codex was unavailable
  (`isolation_profile_unavailable` → `guardrails_disabled`) and that no review was produced, rather
  than fabricating one.
- **If the user chooses to proceed single-model:** the rest of the skill continues Claude-only.
  Concretely:
  - Codex's Phase 1 fresh-eyes pass is skipped — `$RUN/codex_fresh_eyes.json` is never produced.
  - Codex's Phase 2 challenger pass is likewise skipped (same resolver, same failure, no reason to
    re-attempt it independently — and there would be nothing new for it to cross-examine either).
  - Claude's own Phase 2 challenger pass, which is defined as reviewing against
    `$RUN/codex_fresh_eyes.json`, has no Codex findings to cross-examine, since that file doesn't
    exist. Effectively, only Claude's native Phase 1 fresh-eyes findings feed into Phase 3.
  - In Phase 3 synthesis, every surviving finding is Claude-only and, per the resolver's own
    statement, defaults to **Medium** confidence — nothing cross-examined it, so it cannot reach the
    High tier ("both models independently raised it" or "one raised it, the other's Phase 2 pass
    confirms it") and it wasn't refuted either, so it isn't Low/contested.
  - I record this explicitly under `inspection_limits` in the final report: Codex was unavailable
    for this run (`isolation_profile_unavailable` on the sandboxed bridge, `guardrails_disabled` on
    the no-sandbox fallback since no local override exists), the review proceeded single-model per
    the user's explicit choice, and all findings are capped at Medium confidence as a result. I do
    not present the result as if it were cross-examined when it wasn't.
  - The rest of Phase 3 proceeds normally otherwise: rank by severity × confidence, present the
    compact table, expand High-confidence items (none will exist here, given the cap), and end by
    asking which findings, if any, to act on. I still do not auto-apply any fix.

## Summary of what I deliberately do NOT do at this point

- I do not create or point the skill at `.claude/codex-windows-guardrails.local.json` to force Step 2
  to succeed.
- I do not retry Step 1 or Step 2 a second time hoping for a different result.
- I do not silently proceed single-model without the Step 6 `AskUserQuestion` — the degrade path is
  explicit and user-gated, not automatic.
- I do not report the resulting findings as cross-examined/high-confidence when only one model ever
  saw the diff.
