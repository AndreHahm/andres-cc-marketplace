# Investigation: ENG-204 unexplained transition to "In Review"

**Skill invoked:** `linear-github-reconciliation`
**Trigger match:** "why did this issue's status change unexpectedly" — this is one of the skill's own
documented activation phrases, and the request (an unexplained Linear status change with no Wave 2
skill recording it) is exactly the broader-sweep case this skill exists for rather than
`linear-github-linking`'s narrower single-Issue link check.

## Environment note (read this before the findings below)

This session has no live connection to a real Linear workspace, no real GitHub repository state for
this issue, and no invocable instances of `linear-work-management`, `linear-github-linking`, or
`repository-gates` as actual tools. Everything below follows the skill's procedure structurally —
what I would read, how I would compare it, and how I would classify the result — but the concrete
facts about ENG-204 (does a PR exist, what does its evidence history actually say, what is the
configured integration scope) are **unknown**, not omitted for brevity. I have not fabricated a PR
number, commit SHA, branch name, or claimed to have queried anything real. Where I state a
conclusion below, I flag whether it's something the skill's own rules dictate regardless of data, or
a conditional hypothesis that depends on data I don't have.

## Step 1 — Read (procedure step 1)

What this step requires, and what I could/couldn't do in this sandbox:

| Source | What I'd read | Status here |
|---|---|---|
| Linear (via `linear-work-management`) | ENG-204's current status, status-change timestamp/actor, and any status-change audit trail Linear exposes | Not available — no live Linear connection to this workspace/issue in this session |
| Git/GitHub Evidence Record history (via `linear-github-linking`) | The append-only evidence entries recorded against ENG-204 so far — SHAs, PR links, prior `supersedes` chains | Not available — no evidence record for a real ENG-204 exists in this sandbox |
| Current GitHub state (`gh pr view`, `gh_api_readonly.py`) | Whether a branch/PR referencing ENG-204 actually exists, its current state (open/draft/ready), and branch-protection rules | Not available — no real repository/PR to query; I did not run these commands against fabricated targets |
| Repository policy (`repository-gates`) | Whether this repo's Linear↔GitHub native integration is configured to only comment/link (informational-only) or to also drive workflow-status transitions on PR open/ready/merge | Not available — no live policy record |
| Native Linear↔GitHub integration links | The actual configured behavior of the integration (e.g., "move to In Review when a linked PR is opened") | Not available |

Since none of these reads can actually execute here, I cannot produce a real classification —
only the reasoning the skill would apply once they do. That reasoning follows.

## Step 2 — Compare against the authority model

Per `FOUNDATON_CONTRACTS.md`'s model referenced by the skill: **Linear owns execution state, GitHub
owns repository facts.** The relevant question is not "which system changed most recently" (the
skill explicitly forbids timestamp-wins reasoning) but: **is there a GitHub fact (a PR/branch tied
to ENG-204) that legitimately justifies the status Linear now shows, and if so, was it Wave 2 or
something outside Wave 2 that caused the transition?**

"No Wave 2 skill in this session recorded that transition" tells us about *this session's own
action log* — it does not by itself tell us whether the transition is legitimate. Two very different
underlying situations produce the identical symptom the user is reporting:

1. A PR/branch referencing ENG-204 exists in GitHub (created by the user directly, by another
   session, or by tooling outside Wave 2's skill set), and GitHub's **native Linear integration**
   auto-transitioned the issue to "In Review" when that PR was opened — which is standard, often
   intentionally-configured behavior for that integration, not a defect. The gap here is purely
   that no Evidence Record entry was written for it, because no Wave 2 skill was in the loop when
   it happened.
2. GitHub's native integration (or a personal "Code & Reviews" setting on someone's GitHub account)
   is driving Linear status transitions **beyond its configured informational-only scope** — i.e.
   repository-gates' policy says this integration should only comment/link, not change workflow
   status, and it's doing so anyway. This is exactly the scenario the skill's own description names
   as its reason for existing ("a native-automation setting that started changing Linear's workflow
   status when it shouldn't").

Only a real read of `repository-gates`' configured integration scope, plus a real check for a
GitHub artifact referencing ENG-204, can distinguish these. I have neither, so I cannot collapse
this to one answer.

## Step 3 — Classification

Applying the skill's nine-state table honestly to what's actually known right now:

**Provisional classification: `Ambiguous`** — insufficient evidence to classify definitively, because
Steps 1–2's required reads did not execute in this environment.

This is not a non-answer — it's the classification the skill's own rules require when evidence is
incomplete ("Ambiguous — Insufficient evidence to classify," always reported to the user, never
resolved by the skill's own guess). Below is the decision tree that would resolve it to one of the
other eight states once the real reads are possible, so the next actual run of this skill (with live
tool access) has a concrete path rather than starting over:

| If real reads show... | Resolves to | Why |
|---|---|---|
| A GitHub PR/branch referencing ENG-204 exists, and repository-gates confirms the integration is configured to transition status on PR-open (or PR-ready) | **Missing link** | The status change is legitimate native-automation behavior operating within its configured scope; the only real gap is the un-recorded Evidence Record entry. Bounded repair: append a new evidence entry via `linear-github-linking` recording the PR/branch. |
| A GitHub PR/branch referencing ENG-204 exists, but repository-gates confirms the integration is configured informational-only (comment/link only, no status writes) | **Automation drift** | The integration (or a personal Code & Reviews setting) is changing Linear state beyond its configured scope. Per the skill's Failure and Resume section, this must stop consequential downstream Wave 2 workflows until the drift is either accepted as a deliberate config change or corrected at the integration-settings level — and this skill must never reverse-write Linear's status back to fight it. |
| No GitHub artifact can be found that plausibly ties to ENG-204 at all | Not cleanly `External artifact` (that classification is for an *unattributed* branch/PR that exists but isn't linkable — here nothing exists to attribute) — most likely genuinely **Ambiguous**, possibly **Contradictory** if Linear's own audit trail names a GitHub-integration actor with no corresponding GitHub fact to support it | Needs the actual Linear status-change actor/audit-trail read to distinguish; could also mean a human changed the status directly in Linear's UI, which is a legitimate Linear-owned action needing no GitHub-side repair at all. |
| Linear's audit trail attributes the change to a human, not the integration | **Aligned** (if the evidence otherwise checks out) or simply outside this skill's remit — a human-made Linear-owned status change doesn't need a GitHub-side repair | Linear owns execution state; a deliberate human transition is not drift. |

I'm not selecting one branch of this table as "the" answer, because doing so would require inventing
data I don't have (e.g., asserting a PR exists, or asserting the integration is misconfigured) —
exactly what the task instructions and the skill's data-only-boundary rule both prohibit.

## Step 4 — Marking superseded evidence

Not applicable yet: there is no known invalid-SHA evidence entry to supersede in this pass, since no
evidence record was actually read. If the eventual real read surfaces a stale SHA (e.g. from a
force-push after the PR that triggered this transition), the correct action is a new entry via
`linear-github-linking` whose `supersedes` field names the old entry — never an edit to the existing
entry.

## Step 5 — Preview repair (bounded, per classification)

Given the two live-data-dependent outcomes above:

- If **Missing link**: preview repair = one new Evidence Record entry recording the existing
  PR/branch against ENG-204. No Linear field change. Bounded to the evidence entry only.
- If **Automation drift**: preview action = *stop*, not repair. No competing write against Linear's
  status field. The "repair" here is reporting the drift and, if the user wants it corrected, doing
  so at the integration-settings level outside this skill's own write authority — not by writing
  Linear's status back.

Neither of these is a scope-broadening action (no priority/scope/date change), so both stay within
this skill's own bounded-repair authority rather than needing to be routed to
`linear-work-management` directly for a material change.

## Step 6 — Confirm (AskUserQuestion) before any consequential change

Per the skill's Confirmation and Safety rules, reading/comparing/classifying needed no approval (and
none was sought). But no repair has actually been proposed for execution in this pass — because the
classification is `Ambiguous`, there is nothing concrete yet to confirm. Once a real read resolves
this to `Missing link` or `Automation drift`, the next step is exactly the AskUserQuestion checkpoint
the skill mandates before writing anything, framed as one of:

- "A PR/branch referencing ENG-204 was found with no recorded evidence entry — record it now?"
- "GitHub's native integration appears to be transitioning Linear status beyond its configured
  informational-only scope. Downstream Wave 2 workflows are being held pending your decision: accept
  this as a deliberate config change, or should the integration setting be corrected?"

## Step 7 — Delegate

Not executed in this pass — there is nothing approved to delegate yet. Once Step 6 is answered:
`linear-github-linking` would own writing the evidence entry (Missing link case); no Linear-side
write happens in the Automation drift case unless/until the user directs a specific correction, and
even then the correction target is the integration's own settings, not a reverse-write through this
skill.

## Recommended next steps (concrete, for whoever runs this with real tool access)

1. Read ENG-204 directly in Linear — its current status, and if Linear exposes a status-change
   actor/timestamp, whether the actor is the GitHub integration bot or a human.
2. Read the Git/GitHub Evidence Record history for ENG-204 via `linear-github-linking` — is there
   any prior entry at all, and does it reference a PR/branch?
3. Search GitHub for a PR/branch referencing ENG-204 (`gh pr view`, `gh_api_readonly.py`, read-only)
   — does one exist, what's its current state, and does its creation timestamp line up with the
   Linear status-change time?
4. Read `repository-gates`' policy for this repo's configured Linear↔GitHub integration scope —
   specifically, is it scoped to informational-only (comment/link) or does it also drive workflow
   status transitions on PR events?
5. Apply the decision table in Step 3 above to resolve `Ambiguous` into a concrete classification.
6. Only then propose the bounded repair, confirm via `AskUserQuestion`, and delegate to the owning
   provider.

## Quality-gate self-check against the skill's own Testing & Validation checklist

- [x] Classified as exactly one of the nine defined states (`Ambiguous`), rather than left
      unclassified, with the concrete decision tree that resolves it further once real data is
      available.
- [x] No timestamp-wins reasoning used anywhere above.
- [x] No repair was executed or asserted as done — nothing consequential was proposed without the
      data needed to justify it, and the AskUserQuestion checkpoint is explicitly deferred to the
      point real data resolves the ambiguity, not skipped.
- [x] Any eventual repair stays bounded to a single evidence entry or a stop-and-report action —
      never a broad bidirectional sync, and never a scope/priority/date change.
- [x] No fabricated PR numbers, commit SHAs, branch names, or claims of having queried a real
      system.
