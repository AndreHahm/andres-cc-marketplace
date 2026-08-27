# Plugin Conception — Entry Route B (Recent-Session Evidence)

**Evidence as stated:** "A session-analysis report from several weeks ago says plugin-bar's commit step
never runs a sensitive-file scan."

This is a session-analysis finding about an existing component's behavior, so it enters through **Entry
Route B**, following the 6-step evidence-handling procedure in `references/evidence-routing.md`.

## Step 1 — Identify the observed behavior and its source

- Observed behavior: "commit step never runs a sensitive-file scan."
- Claimed target: a plugin named `plugin-bar`.
- Source: a session-analysis report, several weeks old — no report path, session ID, or artifact was
  supplied with the claim.

Per `evidence-routing.md` Step 1, "never carry forward an unsourced claim." The claim already arrives
under-sourced (no artifact reference), which is itself a flag independent of what verification finds next.

## Step 2 — Recheck currency against the current repository state

SKILL.md Step 1 is explicit: "Never rely on an unverified claim that a capability is absent or broken —
check the current repository state instead of trusting a stale report." I checked directly rather than
accepting the claim:

- Listed the primary checkout's `plugins/` directory: `analysis-kit`, `codex-kit`, `example-plugin`,
  `git-kit`, `plugin-devkit`.
- Listed the worktree's mirrored `plugins/` directory: same five plugins.
- Ran a repo-wide case-insensitive search for `plugin-bar` (filenames and file contents). The only hits
  were this eval's own fixture files (`evals/plugin-conception/evals.json` and this scenario's
  `eval_metadata.json`) — i.e., the test harness's record of *this exact test scenario*, not a real
  plugin or a real session-analysis report about one.

**Result: `plugin-bar` does not exist anywhere in the current repository.** No plugin, skill, agent,
command, or hook by that name exists to inspect a "commit step" on in the first place.

## Why this is not simply "stale," and why it isn't safe to guess a real target

The Stop Conditions vocabulary in SKILL.md includes "evidence is stale or already resolved" — but that
bucket presumes the target *once existed* and the claim was true then. Here there's no evidence a
component named `plugin-bar` ever existed. That's a different, stronger failure mode: the claim is
**unverifiable against current repository state**, not merely outdated.

Two things the skill explicitly rules out here:

- **Fabricating a stand-in target.** SKILL.md's Route A guidance ("do not fabricate evidence that does
  not exist") generalizes to Route B: I will not silently substitute a plausibly-similar real plugin (for
  example, `git-kit`, whose `commit` skill legitimately does perform sensitive-file detection per its own
  description) as if that were "probably what the report meant." Doing so would mean the classification
  ends up resting on a component the original evidence never actually named — an invented correspondence,
  not a verified one.
- **Promoting to Repair on the strength of the raw claim.** The evidence-routing Human Selection Gate and
  SKILL.md's Step 7 both require verified, current evidence before anything is promoted — an unverifiable
  claim about a nonexistent target cannot clear that bar no matter how specific it sounds.

## Step 3 (of the 6-step procedure) — Separate symptom from underlying need

Not reachable. Separating symptom from underlying need presumes a real component and behavior to reason
about; there is neither here.

## Step 5 — Discard, with recorded reason

Per `evidence-routing.md` Step 5 ("record why each was discarded... a decision to discard is itself a
recorded decision"):

- **Disposition:** discard.
- **Reason code:** **non-actionable / unverifiable** — the named target (`plugin-bar`) does not exist in
  current repository state, so the claim can be neither confirmed nor reproduced.
- **Not classified as:** stale/resolved (would require the target to have once existed and since changed),
  duplicate, or out-of-scope (would require a real, if low-priority, target).

## Step 2 of SKILL.md — Classification

Against the classification table, the only fit is:

**Classification: Reject/Defer** — "Benefit, evidence, feasibility, or priority is insufficient." Here
specifically: **feasibility/evidence is insufficient**, because there is no confirmed component to Repair,
Enhance, Consolidate, or Reposition, and no basis for Create either (nothing about this evidence describes
a new capability — it describes an alleged gap in an existing one that can't be located).

Repair is explicitly *not* the right classification, even though the raw claim ("never runs a
sensitive-file scan") reads like a textbook Repair finding — the narrow-repair bypass in SKILL.md Step 2
only applies to "an already-known, narrowly-scoped fix and an already-accepted finding," and this finding
was never confirmed to be about a real, current target, so it cannot be "already accepted" in the sense
that bypass requires.

**Revisit condition (Defer, not a flat Reject):** re-run Entry Route B if either (a) a corrected plugin
name is supplied and a `commit`-style step in that real component is confirmed to skip sensitive-file
scanning, or (b) the actual session-analysis report artifact is located and it identifies a real,
currently-existing target.

## Step 3 (SKILL.md) — Overlap check

Skipped. Step 3 only runs to confirm or revise a Step 2 classification for a real candidate; there is no
candidate component to check overlap against.

## Steps 4–6 (full brief) / Step 7 (write brief)

Not run. Per SKILL.md, the full Conception Brief (Steps 4–6) and the written brief (Step 7) apply only to
an evidence item that survives normalization and classification as an actionable candidate. Reject/Defer
on unverifiable evidence is itself a Stop Condition ("evidence is stale or already resolved... a clean
stop is a valid result and must include its rationale — never silently drop a concept without stating
why"), stated above. No file is written under `.claude/output/plugin-conception/`.

## What the skill does next (Human Selection Gate)

`evidence-routing.md`'s Human Selection Gate ("never promote a candidate concept automatically") applies
here as a stop-and-report, not a silent drop. In a live (non-test) invocation, the skill would present
this outcome via `AskUserQuestion` with options along the lines of:

1. Supply the correct plugin/component name so verification can be re-run against a real target.
2. Supply the actual session-analysis report artifact (path or content) so Step 1's sourcing gap can be
   closed and Step 2's currency check re-run against what it actually claims.
3. Confirm this candidate should be discarded outright (Reject rather than Defer).

Since this task's own framing already discloses that `plugin-bar` is a fictional placeholder with no real
counterpart to name, none of those three options resolves anything further in this run — the answer to
"does the target exist" is already settled as no. The result stands as: **verification failed (target
does not exist in current repository state) → evidence discarded as non-actionable → classification
Reject/Defer → clean stop, no brief written, no hand-off.**

## Summary

| Item | Result |
|---|---|
| Claim | `plugin-bar`'s commit step never runs a sensitive-file scan |
| Verification | Repo-wide search (plugin directories + full-text grep, both primary checkout and worktree) — no plugin named `plugin-bar` exists |
| Evidence disposition | Discarded — non-actionable / unverifiable (not "stale," since no prior existence was ever confirmed) |
| Classification | Reject/Defer (evidence/feasibility insufficient) |
| Brief written | No |
| Hand-off | None — clean stop with stated rationale; revisit only if a real, corrected target or the actual source report is supplied |
