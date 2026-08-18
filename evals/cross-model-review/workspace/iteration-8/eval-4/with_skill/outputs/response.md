# Does the First-Send Confirmation fire again on the second invocation?

**Yes — it fires again.** The skill scopes the First-Send Confirmation to *each invocation of the
skill*, not to the Claude Code session, and says so explicitly. Nothing in the skill provides any
mechanism (state file, cache, session flag) that could let a later invocation "remember" an earlier
invocation's consent, so a second run in the same session gets no shortcut around the gate — it asks
again, from scratch, exactly as the first run did.

## The controlling text

The gate is defined in the "Codex dispatch resolver" section, under the heading:

> **First-Send Confirmation (mandatory, once per *invocation of this skill*, not once per session — a
> later, separate invocation always asks again — before the *first* real Codex dispatch this run):**

This is the load-bearing sentence for the question. It does three things explicitly:

1. States the scope unit is *"invocation of this skill,"* not *"session."*
2. Directly negates the alternative reading the question poses ("not once per session").
3. States the consequence in plain language: *"a later, separate invocation always asks again."*

The user's scenario — invoke once, get a report, fix findings, invoke again later in the same
session to review the new diff — is precisely "a later, separate invocation." Per this sentence, the
skill's own answer is that the confirmation fires again on that second run, regardless of same-session
status.

## Reinforcing text: explicit independence from other codex-kit gates

A few lines later, in the same First-Send Confirmation block, the skill goes further and rules out
even a *related* form of cross-invocation reuse:

> "Git-kit's own direct implementation of the first-send-confirmation obligation
> `codex-review-bridge`'s docs assign to any caller — independent of, and not satisfied by, a
> first-send gate any other codex-kit component may already have fired earlier in the session."

This closes a nearby loophole the question doesn't ask about but that the skill anticipates: even if
some *other* codex-kit component (not `cross-model-review` itself) had already gotten a first-send
confirmation from the user earlier in the same session, that would **not** satisfy this skill's own
gate. If a sibling component's earlier consent in the same session doesn't count, then a fortiori an
earlier consent from this *same* skill's own prior invocation doesn't count either — the skill treats
every invocation as needing its own fresh confirmation, full stop.

## Why this design makes sense given the rest of the skill

- **No persisted state to check.** The "Deliberately NOT done" section states: *"No persisted
  artifacts / state machine — `$RUN` is scratch, not committed."* `$RUN` is a fresh `mktemp -d` created
  in Preflight step 3 on every invocation and is never reused across runs. There is no file, variable,
  or session-scoped flag anywhere in the skill that could hold "user already consented" across
  invocations even if the skill wanted to skip the re-ask — the mechanism to remember consent simply
  doesn't exist.
- **The gate covers per-run, diff-specific disclosures, not a generic yes/no.** The confirmation text
  itself (in the same block) requires disclosing *"the reviewer persona and target paths"* for **this
  run**, plus conditionally: (b) whether Step 2's `danger-full-access` path will be used *this run*,
  (c) whether Preflight step 6 found *this run's* diff touching the Codex dispatcher, and (d) whether
  Preflight step 5's `REVIEW_UNVERIFIED`/`REFUTE_UNVERIFIED` flags were set *this run*. Since the
  user's second invocation reviews "an updated diff... that now touches a different set of files,"
  these disclosures are substantively different each time (different target paths, possibly different
  trust-boundary findings) — reusing stale consent from the first invocation wouldn't even be
  semantically valid, since the first confirmation's disclosed facts don't describe the second run's
  actual dispatch.
- **Consistent with the project-wide `disclose-before-overriding-decisions` rule** (an `AskUserQuestion`
  checkpoint's decision should never be silently reused/bypassed for a materially different action) —
  though the skill's own text is sufficient on its own to answer the question without needing to invoke
  that external rule.

## Bottom line

Per the skill's own explicit wording — *"mandatory, once per invocation of this skill, not once per
session — a later, separate invocation always asks again"* — the First-Send Confirmation **fires again**
on the second invocation in the scenario described. It is not silently satisfied by the first
invocation's consent, even though both invocations occur in the same Claude Code session. The skill
scopes the gate strictly to "before the first real Codex dispatch this run," where "this run" resets
with every fresh invocation (backed by the fact that `$RUN` itself is a brand-new scratch directory
each time, per Preflight step 3, with no cross-run state of any kind).
