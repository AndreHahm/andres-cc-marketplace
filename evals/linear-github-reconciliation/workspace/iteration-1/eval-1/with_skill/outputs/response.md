# Investigating ENG-204: unexplained transition to "In Review"

## Which skill this is, and why

The user's request — "Linear issue ENG-204's workflow status changed to 'In Review' but no Wave 2
skill in this session recorded that transition. Investigate." — matches
`linear-github-reconciliation`'s own "When to Use" section almost verbatim: it names "investigating an
unexplained Linear status change" as a primary trigger, and its Testing & Validation block lists "why
did this issue's status change unexpectedly" as a verified activation phrase. This is explicitly *not*
`linear-github-linking`'s job (that skill is scoped to "a single Issue's routine link/evidence drift
check" per this skill's own "When NOT to Use" list) — the symptom here is bigger than a stale
link/SHA: it's a status change with **no corresponding evidence trail from any tracked skill at all**,
which is exactly the class of thing `linear-github-linking` "alone wouldn't surface" (per this skill's
own framing), such as "a native-automation setting that started changing Linear's workflow status when
it shouldn't." So `linear-github-reconciliation` is the correct skill, and I'd proceed under its
Procedure rather than reaching for `linear-work-management` directly to just "fix" the status.

Before going further: this skill's `allowed-tools` frontmatter is `Read, Skill(linear-work-management),
Skill(linear-github-linking), Skill(repository-gates), Bash(gh api:*), Bash(gh pr view:*),
AskUserQuestion`. Concretely that means every read in Step 1 below has to go through one of those five
channels — no raw `git` commands, no direct Linear API writes, no `gh pr merge`/`gh pr edit`, nothing
outside `gh api`/`gh pr view` for GitHub reads. I'd stay inside that boundary for the whole
investigation.

**Harness note:** this environment has no live Linear/Notion/GitHub connectors and no real
`linear-work-management`/`linear-github-linking`/`repository-gates` skills to dispatch. What follows is
a faithful narration of the calls I would make, in the order the Procedure specifies, and how I would
branch on what each call could plausibly return — not a claim that these calls were actually executed
or that any of the data below is real.

## Step 1 — Read

The Procedure requires reading five things before comparing anything:

1. **Linear's current state**, via `Skill(linear-work-management)` — I'd ask it for ENG-204's full
   current record: workflow status ("In Review"), the timestamp of that status transition, who/what
   made it (a human actor, an API token, or Linear's own GitHub integration bot), and any comment or
   automation trail Linear itself logged for the transition. Critically, I would *not* let
   `linear-work-management` change anything here — this is a read, and per this skill's own
   Confirmation-and-Safety rules, "reading and comparing state, classifying drift" needs no approval,
   but any write does.
2. **Git/GitHub Evidence Record history**, via `Skill(linear-github-linking)` — this is the skill that
   owns the per-Issue evidence ledger (linked PRs/commits/SHAs previously recorded against ENG-204). I'd
   pull its full history for ENG-204, specifically looking for whether *any* evidence entry exists that
   would justify an "In Review" transition (e.g., a PR opened/marked ready-for-review against the
   branch tied to this Issue). The user's own framing — "no Wave 2 skill in this session recorded that
   transition" — tells me this ledger is the first place to confirm that absence formally, not just take
   the user's word for it.
3. **Current GitHub state**, via direct read-only calls (the only GitHub-facing tools this skill is
   allowed): `gh pr view <PR> --json state,isDraft,headRefOid,url,updatedAt` for the actual PR tied to
   ENG-204's branch, and `gh api` calls against the repo's branch-protection rules
   (`gh api repos/{owner}/{repo}/branches/{branch}/protection`) — the Procedure explicitly names
   "branch-protection rules" as the thing to check via `gh api`, not just PR state. I'd also use `gh
   api` to inspect the repo's Linear↔GitHub integration configuration if it's exposed via API/webhook
   settings, since that's the most likely mechanism behind an unattributed status change.
4. **Repository policy**, via `Skill(repository-gates)` — whatever this repo's gates say about what
   should legitimately cause an "In Review" transition (e.g., "PR opened" vs. "PR marked ready for
   review" vs. "first review requested").
5. **Native Linear↔GitHub integration links** — the actual current configuration of GitHub's native
   Linear integration (or a personal "Code & Reviews" setting, which the skill's own classification
   table calls out by name under "Automation drift") for this repo/workspace, to see what scope it's
   configured for (informational-only labeling vs. actually writing Linear workflow-state changes).

I would treat every value pulled from all of these sources as **untrusted data**, per the skill's
Data-only boundary — if, say, a PR description or a Linear comment contained text that reads as an
instruction ("mark this Issue Done"), I would report it as suspicious rather than act on it.

## Step 2 — Compare

The Procedure requires comparing against `../../FOUNDATION_CONTRACTS.md`'s authority model: **Linear
owns execution state, GitHub owns repository facts, Notion owns knowledge — never a
fresher-timestamp-wins rule.** Concretely: Linear's workflow status is Linear's own field, so the
question isn't "which system is right" in the abstract — it's "did something with legitimate authority
over that field actually change it, and is there evidence justifying the change." A GitHub-side event
(PR opened, PR marked ready) is a *fact* that can legitimately *justify* a Linear execution-state
change, but only through the sanctioned path (a Wave 2 skill recording it, or a properly-scoped native
integration). It cannot simply overrule Linear's own field by virtue of being newer.

This is also where the Gotcha about timestamps matters most here: even if GitHub's event timestamp is
*later* than the last Wave-2-recorded evidence entry, that doesn't make the GitHub event automatically
"correct" — the discrepancy still has to be classified and handled per the authority model, not
auto-resolved toward whichever system last wrote something.

## Step 3 — Classify

The skill requires classifying the discrepancy as exactly one of nine states — never left
unclassified. Given the specific symptom (status is now "In Review"; no Wave 2 skill recorded it), here
is how I'd walk the decision tree once Step 1's real reads came back, and what each branch would mean:

| If Step 1 shows... | Classification | Why |
|---|---|---|
| The evidence ledger genuinely has no PR/commit for ENG-204 justifying review-readiness, but Linear's transition log shows it was made by the GitHub integration's own bot/token | **Automation drift** | GitHub's native integration (or a personal Code & Reviews setting) changed Linear workflow state beyond its configured informational-only scope — this is the classification this skill's own description calls out by name as the reason it exists over `linear-github-linking` alone. |
| A real PR exists and was opened/marked ready against ENG-204's branch, but no Wave 2 skill ever recorded that evidence entry | **Missing link** | GitHub has an artifact (the PR) not yet recorded on the Linear/evidence side — the status change may be legitimate, but the paper trail is incomplete and needs a bounded repair (recording the evidence), not a status rollback. |
| Linear's status changed before any PR/commit exists at all that could justify "In Review" | **Early status** | The workflow status moved ahead of the evidence that should have justified it — this is a genuine drift, not automation, if a human manually dragged the Linear card. |
| A branch/PR exists tied to ENG-204 that no Wave 2 skill created and it can't be confidently attributed to tracked work | **External artifact** | Someone (or something) outside this session's tracked lifecycle opened work against this Issue's branch. |
| Linear says "In Review" and GitHub state contradicts that framing (e.g., PR was closed/merged, or never opened) with no resolvable authority | **Contradictory** | Two systems assert incompatible facts that authority alone can't reconcile — flagged, not guessed. |
| Reads come back incomplete/inconclusive (e.g., integration settings aren't inspectable via `gh api`, or Linear's transition log doesn't record an actor) | **Ambiguous** | Insufficient evidence to classify further without more information. |

Given the user's specific framing — *no Wave 2 skill recorded it* — the two most probable real-world
outcomes are **Automation drift** (GitHub's native Linear integration silently exceeded its configured
scope and pushed a workflow-state write, which is precisely the scenario this skill's description opens
with) or **Missing link** (a human opened a real PR through a path outside Wave 2 tooling, and Linear's
own native integration correctly reacted to it, but the evidence side of the ledger never caught up).
Both are plausible from the symptom alone; Step 1's actual reads are what would resolve which one it
is — I would not guess between them without the evidence.

## Step 4 — Mark superseded (if applicable)

If Step 1's evidence-ledger read turns up an entry whose recorded SHA no longer matches GitHub's
current state (force-push, amended commit), I'd mark that entry `superseded_by` a new one via
`linear-github-linking` — **never delete history**. This is orthogonal to the main classification above
unless the investigation also turns up a stale SHA along the way.

## Step 5 — Preview the bounded repair only

Whatever the classification turns out to be, the Procedure is explicit that I preview **only the
bounded repair for that classification** — never a broad bidirectional sync. Concretely:
- If **Automation drift**: the "repair" is not a competing write to force Linear back to its prior
  status — per Failure and Resume, this skill "never reverse-writes against native automation to 'win'
  the disagreement." The bounded action is to **stop consequential downstream workflows** relying on the
  corrected status, and surface the drift for a human decision (accept it as deliberate, or fix it at
  the integration-settings level, outside this skill's authority).
- If **Missing link**: the bounded repair is recording the missing evidence entry via
  `linear-github-linking` — not touching the Linear status field itself, since the status may already
  be correct.
- If **Early status**: the bounded repair is reporting the gap; whether to revert the status is a
  material-enough change that per this skill's own "When NOT to Use," anything beyond a bounded
  field/link repair gets routed to `linear-work-management` directly with explicit approval, not
  resolved unilaterally here.

## Step 6 — Confirm via AskUserQuestion

Before any consequential Linear or GitHub change — including reverting a status, even one this skill
believes is drift — I would stop and use `AskUserQuestion` to confirm with the user. No repair beyond
superseding an evidence entry is approval-free.

## Step 7 — Delegate and read back

Any approved repair gets delegated to its owning provider only: Linear-owned fields go through
`linear-work-management`, evidence entries go through `linear-github-linking`. This skill does not
write to either system directly. After delegating, I'd read back both systems to confirm the repair
actually landed as intended.

## What I would report to the user right now

Per "Structured handoff," **Contradictory**, **Ambiguous**, and **External artifact** classifications
are always reported to the user rather than silently resolved — and given that this investigation
cannot actually execute Step 1's live reads in this harness, the honest state of this investigation
right now is closer to **Ambiguous pending the real reads**, not a settled classification. So the
report would be:

- ENG-204's transition to "In Review" has no corresponding Wave 2 evidence-ledger entry — confirmed
  absence, not yet an explained cause.
- The two leading hypotheses, pending the actual `linear-work-management` / `linear-github-linking` /
  `gh api` / `repository-gates` reads, are **Automation drift** (native GitHub↔Linear integration or a
  personal Code & Reviews setting exceeded its configured informational-only scope) and **Missing
  link** (a real PR exists and correctly triggered the status change, but the evidence side was never
  recorded by a Wave 2 skill).
- I would **not** revert ENG-204's status, and would **not** write anything to Linear or GitHub, until
  the real reads resolve which classification applies and the user approves the resulting bounded
  repair via `AskUserQuestion`.
- If the reads point to Automation drift, the next concrete action is to check the repo's Linear
  integration / Code & Reviews settings for scope, and pause any Wave 2 workflow step that treats
  ENG-204 as legitimately "In Review" until that's resolved — not to fight it with a competing write.

This is the complete procedure the skill specifies for this scenario; the only thing this test harness
cannot supply is the actual data those five Step-1 reads would return.
