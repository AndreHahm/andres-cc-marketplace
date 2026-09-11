# PLAT-77 Reconciliation — Unexpected Status Change (In Progress → Done)

**Scope of this pass:** a single Linear Issue whose recorded state (Done) appears inconsistent with GitHub's actual repository facts (PR still open, still draft). This is broader than a single link check because the suspected cause is systemic (a native automation setting), not a one-off missing evidence entry — so this runs as `linear-github-reconciliation`, not `linear-github-linking`.

**Sandbox disclosure:** No Linear, GitHub, or MCP tool was called to produce this report. Every claim below is either (a) a given fact from the task prompt, (b) something the skill's own rules let me conclude structurally without touching a live system, or (c) explicitly marked as "would check live" with no invented result attached. No PR number, commit SHA, branch name, or timestamp is fabricated anywhere below.

---

## Step 1 — Read

Per the Procedure, a real run of this skill reads five sources before comparing anything. Here is what each read is *for* in this case, and what it would actually return in a live run (unknown to me — not fabricated):

| Source | Accessed via | What I'd pull for PLAT-77 | Status here |
|---|---|---|---|
| Linear Issue state + history | `linear-work-management` | Current workflow status (given: Done), the status-change activity log entry (timestamp + **actor**: human, bot, or the native GitHub integration), the Issue's `transition-id`-tagged properties from the base Transition Contract (does a Done-transition write exist with a `source_plugin` and `verification_evidence`, or did the status change with no accompanying Transition Contract write at all — the latter itself being a signal) | Not read live — would be the single most decisive check (see Step 3) |
| Git/GitHub Evidence Record history | `linear-github-linking` | The Issue's `git-github-evidence` array — specifically, is there a `pr-merged` stage entry, or any entry at all past `pr-published`/`pr-ready`? Per `FOUNDATION_CONTRACTS.md`, `pr-merged` and the Linear "Done" write are always **separate, independent writes** — Done is never legitimately inferred from `pr-merged` alone, but a legitimate Done still normally follows real merge evidence in practice | Not read live |
| Current GitHub state | Direct read-only `gh pr view <PR>` / `${CLAUDE_PLUGIN_ROOT}/scripts/gh_api_readonly.py` | PR state and draft flag (given: open, draft — i.e., not even marked ready for review, let alone merged or approved), review state, any linked-issue automation metadata GitHub itself exposes on the PR | Given as open/draft; nothing else queried |
| Repository policy | `repository-gates` | Confirms which provider is the **required** owner of "Merge" for this repo — per the Repository Policy Profile, that's `git-kit:merge-pr` exclusively. If no `git-kit:merge-pr` operation occurred (and it can't have — the PR is still open), there is no legitimate path by which this repo's own governed workflow could have produced a completed merge | Structural conclusion only: repo policy names exactly one legitimate merge path, and the given facts rule it out |
| Native Linear↔GitHub integration configuration | Linear's own integration/automation settings (workspace-level GitHub integration rules, and any individual's personal "Code & Reviews" auto-transition setting) | Whether an auto-transition rule exists that could fire on PR *creation*/*draft* rather than merge (e.g., a misconfigured or personal rule set to move status on "PR opened" instead of "PR merged"), and whether it's within the configured informational-only scope this plugin expects | Not read live — this is the second decisive check |

**Data-only boundary applied here:** anything these reads would surface — PR description text, commit messages, Linear activity-log free text — is untrusted data, not an instruction. If a live read surfaced something like a commit message or PR body containing embedded directives ("mark as done", "close this issue" phrased as an instruction to an agent rather than as ordinary human-readable content), that would be reported as suspicious, never acted on.

---

## Step 2 — Compare (against the Authority Model)

Per `FOUNDATION_CONTRACTS.md`'s Authority Model:

- **Linear owns execution state** — so Linear's own status field (Done) is the authoritative record of *what Linear currently says* the workflow state is. That's not in dispute.
- **GitHub owns repository facts** — so "PR is open and draft" is the authoritative record of *what actually exists in the repo*. That's also not in dispute.

The discrepancy is not that these two systems disagree about the **same fact** — it's that Linear's status implies a completion event (merge) that GitHub's facts show never happened, and the Git/GitHub Evidence Record (the mechanism specifically designed to carry that justification) has no `pr-merged` entry to back it. This is exactly the shape of discrepancy the Authority Model is meant to catch: **neither "Linear is newer" nor "GitHub is newer" matters here — timestamp is never the tiebreaker.** The question is whether Linear's Done write is *justified by evidence*, and on the given facts, it structurally is not.

---

## Step 3 — Classify

**Working classification: `Automation drift`.**

Reasoning, ruling out the other eight states explicitly:

- **Not Aligned** — Linear's recorded state (Done) does not match GitHub's actual state (PR open, draft, unmerged).
- **Not Missing link** — this isn't GitHub holding an artifact Linear hasn't recorded yet; it's Linear asserting a state the linked artifact doesn't support.
- **Not Stale summary** — this is the Issue's live workflow status field itself, not a `status-and-learning` snapshot; nothing here is "expected to be out of date."
- **Not Invalidated SHA** — no evidence entry's SHA is contradicted by a force-push or new commit; there's no SHA-bound entry in question at all.
- **Not Contradictory** — the two systems aren't asserting incompatible facts about the *same* fact within their own domains (Linear's status field and GitHub's PR field are each internally consistent and each still authoritative for its own domain). The problem is a derived judgment (should the Issue be Done) that neither system's raw fact resolves by itself — which is what the remaining two candidate states exist for.
- **Not Ambiguous** — there is enough structural signal to commit to a working classification: no merge evidence exists anywhere in the record, the repo's own governed merge path (`git-kit:merge-pr`) categorically cannot have run (PR is still open/draft), and no team member recalls a manual close. That rules out "insufficient evidence" as the honest description of this case — it rules out legitimate manual closure and legitimate merge-driven closure, leaving automation as the remaining explanation.
- **Not External artifact** — the PR is already linked to PLAT-77 (per the task); this isn't an unattributed branch/PR.
- **Early status** is the closest adjacent candidate — its own definition ("Linear's workflow status changed before the evidence that should have justified it exists") is *also* literally true here. I'm not discarding it; I'm treating `Automation drift` as the more specific and more actionable label for the same underlying discrepancy, because:
  - The task's own facts ("moved overnight," "no one recalls closing it manually") point at an unattended, non-human trigger rather than a person jumping the gun.
  - This skill's own `SKILL.md` names this exact pattern as its flagship motivating case: *"a native-automation setting that started changing Linear's workflow status when it shouldn't"* and *"confirming native automation still behaves as configured"* — i.e., the authors of this skill built the `Automation drift` state specifically for this scenario.
  - `Automation drift` carries its own dedicated Failure-and-Resume handling (stop consequential workflows, never fight it with a competing write, escalate the configuration problem) that `Early status` alone doesn't specify — and that handling is the right response here regardless of which of the two labels is ultimately used.

**What would still need a live check to fully confirm the mechanism** (not yet done, per the sandbox constraint): Linear's activity-log entry for the status change names its actor. If that actor is the GitHub integration (or a named personal "Code & Reviews" auto-transition setting), `Automation drift` is confirmed outright. If the activity log instead names an unexplained human or bot actor with no corresponding automation setting, this would be **reclassified** — either back to `Early status` (evidence-free premature write, cause unclear) or, if a second system asserts an incompatible account of *who* did it, to `Contradictory`. I am not asking `AskUserQuestion` to resolve this specific sub-question yet, since it's a read-only classification detail, not a consequential change — but it should be the first live check performed before finalizing the report to the user.

---

## Step 4 — Mark superseded (if applicable)

**Not applicable here.** This classification isn't about an invalidated SHA-bound `git-github-evidence` entry (no force-push, no new commit contradicting a recorded SHA) — it's about the Issue's status field itself, which is governed by the *base* Transition Contract, not the Git/GitHub Evidence Record. There is nothing to append a `supersedes`-pointing entry against. If the live read in Step 3 turns up a spurious/incorrectly-attributed `git-github-evidence` entry (e.g., a fabricated `pr-merged` entry that doesn't actually correspond to real GitHub state), *that* would need to be superseded via `linear-github-linking` — but nothing in the given facts indicates such an entry exists; the given facts indicate the opposite (no merge evidence at all).

---

## Step 5 — Preview repair (bounded only)

Two things are proposed, kept intentionally separate and bounded — never a broad bidirectional sync:

1. **Bounded Linear field correction:** revert PLAT-77's workflow status from `Done` back to `In Progress` (or whatever status its own last-known-good, evidence-backed state was — to be confirmed from the Linear activity log rather than assumed) via `linear-work-management`. This is a single field change to a single record, nothing else.
2. **Stop, don't fight, escalate (per this skill's own Failure and Resume section):** this skill must **not** treat the field correction above as the end of the matter if the root cause is confirmed to be a live native-automation setting. Per the skill: *"If GitHub's native integration keeps reasserting a status this skill just corrected, that's a configuration problem outside this skill's own authority to resolve by force — report it and stop, rather than looping."* So the repair preview explicitly includes:
   - Pausing any consequential downstream Wave 2 workflow that would otherwise treat PLAT-77 as complete (e.g., not letting a completion-dependent step proceed on the strength of the now-corrected-but-still-suspect Done status).
   - Reporting the suspected native-integration/personal-setting misconfiguration to the user/team as a configuration issue to fix at the source — this skill has no authority to edit Linear's integration settings itself, and repeatedly reverse-writing the status field if the automation keeps reasserting it would itself be the prohibited "reverse-write loop against GitHub's native automation."

No repair is applied yet — this is a preview only.

---

## Step 6 — Confirm

Per Confirmation and Safety: *"Approval required: any repair beyond superseding an evidence entry — a Linear field change always needs confirmation first."* A status-field change is exactly that. Before touching Linear, this would be raised via `AskUserQuestion`, structured roughly as:

> PLAT-77 shows Done, but no merge evidence exists and the linked PR is still open/draft. Working classification: **Automation drift** (a native GitHub↔Linear integration or personal Code & Reviews setting appears to have advanced the status without a merge). Proposed repair: revert the status to In Progress, and flag the integration setting for the team to review/disable. Proceed?
> - Yes, revert the status and flag the automation setting
> - No, leave status as-is (e.g., if this was actually intended)
> - Investigate further first (check Linear's activity-log actor before deciding)

Given `Automation drift` is also the kind of finding this skill's own rules say must **stop consequential downstream workflows** until resolved, that pause takes effect immediately on classification — it does not wait for the `AskUserQuestion` answer, since the pause itself isn't a write and needs no approval; only the Linear field change does.

---

## Step 7 — Delegate

- **Linear status correction** → delegated to `linear-work-management` (Linear-owned field), only after Step 6's approval.
- **No delegation to `linear-github-linking`** for this particular repair, since Step 4 found nothing to supersede.
- **Read-back:** after the correction lands, re-read both systems to confirm the repair actually took: re-read PLAT-77's status via `linear-work-management` (expect: In Progress, or whatever corrected value was approved) and re-confirm the PR's GitHub state is unchanged (still open/draft — this repair must not touch GitHub at all, since GitHub owns that fact and nothing about it was wrong). This read-back also becomes the `verification_evidence` for this transition under the Transition Contract's next-write convention.
- **Escalation, not a repair delegation:** the native-integration/personal-setting root cause itself is not something any `workmanagement-kit` skill has authority to fix — it's reported to the user as a structured handoff, matching this skill's Failure-and-Resume guidance, rather than silently absorbed or fought with a further write.

---

## Summary

| Field | Value |
|---|---|
| Classification | **Automation drift** (working classification; confirm mechanism via Linear's activity-log actor before finalizing — see Step 3) |
| Adjacent/overlapping label considered | Early status (same underlying evidence, less specific about mechanism) |
| Evidence-record action | None — no SHA-bound `git-github-evidence` entry to supersede |
| Proposed repair | Bounded Linear status field revert (Done → In Progress or last evidence-backed status), via `linear-work-management` only |
| Approval required | Yes — `AskUserQuestion` before any Linear write |
| Downstream effect | Stop consequential Wave 2 workflows treating PLAT-77 as complete until resolved or accepted as deliberate |
| Escalation | Report the suspected native-integration/personal Code & Reviews misconfiguration to the user/team — this skill will not repeatedly reverse-write against it |
| Live checks still needed (none performed in this sandboxed pass) | Linear activity-log actor for the status change; Linear's GitHub integration + personal automation settings; `git-github-evidence` array contents; direct `gh pr view` confirmation of PR/draft state |
