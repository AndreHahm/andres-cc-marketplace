# Does the user learn about `REVIEW_UNVERIFIED` before Codex is dispatched, or only in the final report?

**Before.** The skill explicitly requires disclosing this to the user via a mandatory `AskUserQuestion`
gate that must fire before the first real Codex dispatch of the run, and it explicitly forbids treating
the final report's `inspection_limits` entry as a substitute for that pre-dispatch disclosure. Below is
the exact chain of where this happens.

## Step 1 — Preflight step 5 sets the flag (before any dispatch)

Preflight step 5 (`## Preflight`, item 5) is where `REVIEW_UNVERIFIED=1` (or `REFUTE_UNVERIFIED=1`) gets
set:

> "A `git show` failure (non-zero exit, or an empty `$RUN/review.md`/`$RUN/refute.md`...) means the file
> doesn't exist on `$BASE` yet (e.g. this skill's own not-yet-merged first run). Once the chained
> invocation has returned and its echoed state captured, fall back... but never silently: set
> `REVIEW_UNVERIFIED=1` / `REFUTE_UNVERIFIED=1` and record it in Phase 3's `inspection_limits`
> ('reviewer instructions were not trust-boundary-verified against $BASE this run')."

This is exactly the scenario in the question: the skill's own `prompts/review.md` doesn't exist on
`$BASE` yet because this is the skill's first, not-yet-merged run, so the working-tree copy at
`${CLAUDE_PLUGIN_ROOT}/skills/cross-model-review/prompts/review.md` is `Read` and `Write`-ten into
`$RUN/review.md` as a fallback, and the flag is set. Note that at this point the instruction text only
says the flag gets *recorded in Phase 3's `inspection_limits`* — read in isolation, step 5 alone could
look like a report-only, after-the-fact disclosure. That impression is corrected by the very next
section.

## Step 2 — The Codex dispatch resolver's First-Send Confirmation (before dispatch)

The `## Codex dispatch resolver` section defines a mandatory, pre-dispatch gate — **First-Send
Confirmation** — that every Codex dispatch in Phases 1 and 2 must pass through. It is explicit that this
happens "once per *invocation of this skill*... before the *first* real Codex dispatch this run":

> "**First-Send Confirmation (mandatory, once per *invocation of this skill*, not once per session — a
> later, separate invocation always asks again — before the *first* real Codex dispatch this run):**
> `AskUserQuestion` — name the reviewer persona and target paths, and disclose plainly: (a) the
> dispatched process can read anything under the repository root regardless of `--target-paths`, which
> only scopes what it's checked against; (b) **if Step 2 triggers, the dispatch runs
> `danger-full-access`**...; (c) if Preflight step 6 found the diff touching the Codex dispatcher itself,
> that it wasn't trust-boundary-verified against `$BASE`; and **(d) if Preflight step 5 set
> `REVIEW_UNVERIFIED` or `REFUTE_UNVERIFIED`, that the reviewer instructions governing this dispatch came
> from the working tree, not `$BASE` — before Codex is judged against them, never deferred to
> `inspection_limits`.** Ask before the backend resolves, covering both outcomes. Options: 'Send to Codex
> for this run' / 'Stay Claude-native for this run'."

Item **(d)** is the load-bearing clause for this question. It:

1. Names the exact scenario in the question (`REVIEW_UNVERIFIED`/`REFUTE_UNVERIFIED` set by Preflight
   step 5) as one of four mandatory disclosure items in this gate.
2. States the disclosure must happen "before Codex is judged against them" — i.e., before the dispatch
   that uses those unverified instructions actually runs.
3. **Explicitly rules out the reading the question is testing for** — that this is only surfaced in the
   final report — with the clause "never deferred to `inspection_limits`." The skill anticipates exactly
   the ambiguity that step 5's own wording ("record it in Phase 3's `inspection_limits`") might create,
   and closes it here by saying the `inspection_limits` record is not sufficient on its own; the
   pre-dispatch `AskUserQuestion` disclosure is mandatory in addition to it.
4. Is asked "before the backend resolves, covering both outcomes" — meaning the disclosure happens before
   the skill even attempts Step 1 (`codex-review-bridge`) or falls back to Step 2
   (`codex-windows-guardrails`), not just before whichever one ultimately succeeds.

So concretely, in the scenario posed: after Preflight sets `REVIEW_UNVERIFIED=1` because
`plugins/git-kit/skills/cross-model-review/prompts/review.md` doesn't exist yet on `$BASE`, and before
Phase 1's Codex call is attempted (`Dispatch with --reviewer-type fresh-eyes-reviewer...` in `## Phase 1`),
the skill must stop and run the First-Send Confirmation `AskUserQuestion`, telling the user plainly that
the reviewer instructions governing this dispatch came from the working tree rather than the
trust-boundary-verified `$BASE` copy. Only after the user answers "Send to Codex for this run" does the
resolver actually attempt Step 1 (`bridge-invoke.mjs`) or fall back to Step 2
(`guarded-dispatch.mjs`). If the user instead answers "Stay Claude-native for this run," the skill "enter[s]
single-model mode immediately, before any dispatch is attempted" (the paragraph immediately following
First-Send Confirmation), so Codex is never dispatched with the unverified instructions at all — but
critically, the disclosure already happened *before* that choice was offered/made, not after.

## Step 3 — Phase 3's `inspection_limits` (after the fact, in addition to, not instead of, Step 2)

Separately, Phase 3 (`## Phase 3 — Synthesize and report`) also surfaces this in the final report:

> "Note any `inspection_limits` from either side, including:... Preflight step 5's unverified-instructions
> fallback if either `REVIEW_UNVERIFIED` or `REFUTE_UNVERIFIED` was set..."

This is real and required, but per item (d) above it is explicitly a *second*, persistent record of a
fact the user was already told before dispatch — not the first or only place the user learns it. The
skill's own language ("never deferred to `inspection_limits`") makes clear this final-report line is
not allowed to be the sole disclosure mechanism.

## Answer

The user learns about the unverified/working-tree-fallback reviewer instructions **before** Codex is
actually dispatched with them — via the mandatory, pre-dispatch **First-Send Confirmation**
`AskUserQuestion` defined in the `## Codex dispatch resolver` section, whose disclosure item (d) is
triggered directly by Preflight step 5 having set `REVIEW_UNVERIFIED`/`REFUTE_UNVERIFIED`. That gate runs
"before the *first* real Codex dispatch this run" and "before the backend resolves," i.e., strictly prior
to both Phase 1's Codex call (`## Phase 1 — Independent review`) and any Phase 2 Codex call. The skill
text goes out of its way to forbid the alternative reading the question raises — that this could be
disclosed only afterward in Phase 3's `inspection_limits` — with the explicit phrase "never deferred to
`inspection_limits`." Phase 3 (`## Phase 3 — Synthesize and report`) does *also* record the same fact in
the final report's `inspection_limits`, but that is a redundant, persistent record for the written
output, not the mechanism by which the user first learns of it — the user has already been asked and has
already answered (Send to Codex / Stay Claude-native) before any dispatch using those unverified
instructions occurs.
