# Re-Check State Before a Side-Effecting Action

A skill, workflow, hook, or script that observes external async state it doesn't fully control (a
CI run's conclusion, a bot's reaction, a PR's head SHA) MUST re-check that state immediately before
any side-effecting action based on it (posting a comment, rerunning a workflow, merging) — never
reuse a check from an earlier step, however recent — and MUST handle the observed value's full
state space, not a pass/fail binary.

## Incorrect

Checks the run's conclusion once, does other work, then acts on the stale value later — and only
handles pass/fail:

```markdown
Step 4: `gh run view <id> --json conclusion` → conclusion is `failure`.
Step 5: ask the user whether to proceed (a pause of unknown length).
Step 6: since step 4 already showed `failure`, rerun the workflow.
```

By step 6 the run may have already been retried or resolved by someone else — the step-4 check is
stale — and `cancelled`/`neutral`/`skipped`/`action_required`/`stale`/`startup_failure` were never
considered as possible outcomes.

## Correct

Re-checks immediately before the side-effecting call, gates on `status` before trusting
`conclusion` at all, and branches on the full enum:

```markdown
Step 6: `gh run view <id> --json status,conclusion` (re-checked here, not inherited from step 4).
  - `status` is `queued` / `in_progress` / `requested` / `waiting` / `pending`
                                  → stop, a retry is already underway; don't act yet.
  - `status` is `completed`, `conclusion` `failure` / `timed_out`
                                  → rerun.
  - `status` is `completed`, `conclusion` `success`
                                  → stop, already resolved.
  - `status` is `completed`, `conclusion` `cancelled` / `neutral` / `skipped` /
    `action_required` / `stale` / `startup_failure`
                                  → stop, report the unexpected conclusion.
```

`conclusion` is only meaningful once `status` is `completed` — reading it without checking `status`
first misses the case where another actor already started a fresh run. Get both enums from the
tool's current schema (e.g. `gh run list --help`'s `--status` list) when writing this kind of
check — don't hand-write a shorter list from memory, since a partial list teaches the same
incomplete-branch mistake this rule exists to prevent.

## Enforcement

No automated hook backs this rule, and none is added here: whether a specific side-effecting call
re-checked its own dependency immediately beforehand is a semantic judgment about a skill's control
flow that a mechanical `PreToolUse` hook cannot reliably verify. Per `rule-development`'s own
enforcement-limits guidance, that means this `MUST` does **not** carry the deterministic guarantee a
hard directive around an irreversible action is supposed to have — compliance depends on
author/reviewer attention at Build/Self-Review time, a non-deterministic, explicitly accepted gap,
not a substitute for the missing enforcement mechanism. This is the same disclosed-limitation model
`route-through-git-kit-lifecycle-skills.md` uses for its own marker-handshake guardrail ("stops
accidental bypass... not a deliberately adversarial agent"): treat this rule as a strong authoring
convention to catch in review, not a self-enforcing gate.

## Why

PR #51 (`codex-review-recovery`) is documented in `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` as the
richest PR in the review dataset — 7-8 Codex rounds, ~15 findings — and this exact shape (a
TOCTOU-class stale check feeding a side-effecting action) recurred in a new place almost every
round from round 2 through round 7, each fixed independently because each round's fix addressed
only the one instance flagged that round.

This is the TOCTOU class recurring at the skill-authoring level, not just the code level —
[[verify-tool-behavior-before-instructing]] catches "does this tool/API behave the way I assumed it
does," but says nothing about "has the state I already correctly observed changed by the time I act
on it." The two failure modes are independent, and both showed up repeatedly in the same PR.
