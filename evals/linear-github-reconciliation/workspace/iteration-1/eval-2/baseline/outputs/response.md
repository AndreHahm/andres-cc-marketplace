# Investigation: PLAT-77 Status Change (In Progress → Done)

## 0. Ground rules for this write-up

I have **no live connection** to Linear or GitHub in this session — I did not and cannot query the actual PLAT-77 issue, its history, or the linked PR. Everything below that reads as "check X" is a *recommended investigation step*, not a reported finding. Anything I label a "fact" is limited to what was stated in the prompt. Everything else is a ranked hypothesis to be confirmed or ruled out against the real systems.

**Given facts (as stated, not independently verified by me):**
- PLAT-77 changed status from "In Progress" to "Done" overnight.
- The GitHub PR linked to PLAT-77 is still **open** and still marked **draft**.
- No team member recalls performing the status change manually.

That combination — issue Done, but linked PR neither merged nor even marked ready-for-review — is the central anomaly. Almost every legitimate Linear↔GitHub status-sync path moves an issue to "Done" only on a **merge** event (or, in some misconfigured setups, a "ready for review" event). A draft, open PR should not have triggered either. So the leading theory going in is: **something moved this issue outside the normal, intended sync path** — either a different piece of automation, a human error, or a sync event tied to the wrong PR/issue.

---

## 1. Hypotheses, ranked by plausibility

### H1 — Wrong-issue keyword match (typo / copy-paste in a commit or PR that *did* merge)
Linear's GitHub integration (and GitHub's own issue-closing keywords) scan commit messages and PR descriptions for phrases like `Closes PLAT-77`, `Fixes PLAT-77`, `Resolves PLAT-77`. If a **different PR or a direct commit to the default branch** (a hotfix, an unrelated feature, a squash-merge) accidentally referenced `PLAT-77` — e.g., a fat-fingered issue number, a copy-pasted commit message template, or someone working on PLAT-177/PLAT-7 and mistyping — that merge would close PLAT-77 even though the PR *actually* meant to close it is still an open draft. This is one of the most common real-world causes of "issue closed but its own PR is untouched," because the two PRs are unrelated in the person's mind but not to the keyword parser.

**How to check:** Search the repo's merged commit history and PR titles/descriptions (across *all* recent PRs, not just the one linked to PLAT-77) for the literal string `PLAT-77` in the relevant overnight window. Also check for adjacent issue IDs (PLAT-7, PLAT-770, PLAT-177) in case of transposition.

### H2 — A separate PR/branch is (or was) linked to PLAT-77, and *that one* merged
Linear allows multiple branches/PRs to be associated with one issue (via branch-name convention, manual linking, or magic words in multiple PRs). It's possible a second PR — not the draft one the team is watching — exists, referenced PLAT-77, and merged, triggering the auto-transition. The draft PR everyone is looking at may be stale, superseded, or a parallel/rework branch.

**How to check:** On the Linear issue, look at the **"Linked PRs / Attachments"** panel — Linear typically lists every GitHub PR/branch that got associated, not just one. Look for a second, merged PR.

### H3 — PR was merged, then reverted/force-pushed/reopened, and Linear's one-directional sync didn't roll the status back
Some integration configs move the issue forward on `merged` events but have no listener for `reopened` or "merge reverted" — because from GitHub's model, an issue is either "merged" (permanent) or it isn't; a revert typically shows up as a *new* PR/commit, not as the original PR un-merging. But: if someone (a) merged the PR, (b) that triggered Done, (c) then something caused the merge to be undone and the PR to show as open/draft again (e.g., a bad merge, a branch protection issue, or the PR was manually reopened and re-marked draft to redo the work) — the Linear status would be stale/wrong, not "caused by nothing." This is less likely to produce a genuinely *still-draft* PR (a truly reverted merge PR usually shows as merged/closed, not draft), but worth ruling out via the PR's own timeline/event log.

**How to check:** PR's GitHub "Timeline" tab — look for `merged`, `reverted`, `reopened`, `convert to draft`, `head ref force-pushed` events in the overnight window, in that order.

### H4 — Parent/sub-issue auto-completion
If PLAT-77 is a **parent issue** with sub-issues, some Linear workflow configurations auto-complete a parent when all its sub-issues reach a terminal state. If a batch of sub-issues got closed overnight (correctly or incorrectly), the parent could have cascaded to Done independent of the PR entirely — the linked PR being draft/open would then be a red herring / separately still-open piece of work.

**How to check:** Look at PLAT-77's sub-issue list and their status-change timestamps; see if they cluster around the same overnight window.

### H5 — Linear workflow automation / SLA / stale-issue rule
Linear supports team-level "Workflow automations" (e.g., auto-move issues after N days of inactivity, on label change, etc.) and Triage/SLA features. Depending on config, one of these could move an issue to a terminal state without any GitHub involvement at all. This is more commonly configured to move issues to "Cancelled"/"Backlog" than "Done," but a misconfigured automation rule is not out of the question, and the "overnight" timing (i.e., an off-hours scheduled action rather than a human at a keyboard) is consistent with an automation firing on a timer.

**How to check:** Linear → Team Settings → **Workflows/Automations** — review any rule whose target state is "Done" and whose trigger could plausibly fire unattended.

### H6 — Third-party integration / script with API write access (Zapier, Make, n8n, internal tooling, CI job)
Any OAuth app or personal API key with write access to the workspace could have moved the issue — e.g., a misconfigured Zapier/Make scenario syncing from another system (Jira migration script, a status-sync bot, a nightly reporting/cleanup job) that matched PLAT-77 incorrectly, or a bug in an internal tool. "Overnight" and "no one recalls doing it manually" both point toward *something automated running on a schedule*, which fits this hypothesis well.

**How to check:** Linear → Settings → API → review active **OAuth applications** and **personal API keys**, and check for any "Actor" on the issue's history entry that isn't a human user (Linear's audit trail typically labels changes made via the GitHub integration as "Linear" or shows the GitHub bot, and changes via personal API keys as the token owner).

### H7 — Human error, then forgotten (least likely given "no one recalls," but not zero)
Someone doing a bulk status update (multi-select in a board/list view) across several issues may have swept PLAT-77 in by accident and not noticed, especially late at night / end of a session. People are also often reluctant to say "actually that might have been me" for a small clumsy mistake — "no one recalls" is suggestive but not conclusive proof it wasn't manual.

**How to check:** Linear's issue **Activity/History** log shows the actor and exact timestamp for the state change. If it shows a named human user (not "GitHub" or a bot/integration name), and especially if several *other* unrelated issues changed status at the exact same second, that's a strong bulk-edit signature.

### H8 — Duplicate-issue merge
If PLAT-77 was marked as a duplicate of another issue (or another issue was merged into it) via Linear's "merge issues" / "mark as duplicate" feature, that action can force a state change as a side effect, independent of any GitHub activity.

**How to check:** Look at the issue for a "duplicate of" relation or merge history entry.

---

## 2. Investigation checklist (in the order I'd actually run it)

1. **Pull PLAT-77's Activity/History log in Linear first.** This is the single highest-signal artifact: it should show *who or what* changed the status and the exact timestamp. This alone often resolves whether it's H1/H2/H3 (GitHub-attributed), H4 (cascade from sub-issues), H5 (workflow-automation-attributed), H6 (API-token/integration-attributed), H7 (a named human), or H8 (merge/duplicate event).
2. **Check the PR's own GitHub timeline** for the same overnight window — look specifically for any `merged`/`closed`/`reopened`/`ready_for_review`/`convert_to_draft` events, not just its current state.
3. **Check for other PRs/branches linked to PLAT-77** in Linear's attachment panel — is the draft PR really the *only* GitHub object associated with this issue?
4. **Search recent merged PRs/commits repo-wide for the literal string "PLAT-77"** (and adjacent IDs like PLAT-7, PLAT-177, PLAT-770) to catch a keyword-close from an unrelated PR.
5. **Check the team's Linear→GitHub integration settings** (Settings → Integrations → GitHub) to confirm exactly which GitHub event is mapped to which Linear state — confirm "Done" is mapped only to `merged`, not also to `ready_for_review` or `opened` (a misconfiguration here would itself explain premature auto-closing on some other, non-merge PR event).
6. **Check whether PLAT-77 has sub-issues** and whether their completion timestamps cluster with the status change (H4).
7. **Check Workflow Automations / SLA rules** at the team level for any rule targeting "Done" (H5).
8. **Check active OAuth apps / API keys** with workspace write access, and whether any scheduled job (CI, Zapier/Make/n8n, internal script) ran overnight (H6).
9. **Ask the team directly, pointed at specifics** rather than "did anyone do this": "did anyone merge a different PR referencing PLAT-77," "did anyone run a bulk edit/migration script last night," "is there a sync tool syncing from Jira/another Linear workspace." A specific question is far more likely to jog someone's memory than a general one.
10. **Check git log on the default branch** for any commits merged overnight that reference PLAT-77, independent of what Linear's integration parsed — this cross-checks step 4 from the git side rather than the Linear side.

---

## 3. Most likely root cause (working conclusion, to be confirmed by step 1 above)

Given the specific shape of the anomaly — **issue Done, but its own linked PR is still open and in draft** — the two strongest candidates are:

- **H1/H2: a keyword match from a different, actually-merged PR or commit** (wrong issue number, or a second branch associated with PLAT-77 that merged while the visible draft PR did not). This is the single most common real-world cause of exactly this symptom pattern, and it doesn't require any human to consciously "close the issue" — which fits "no one recalls doing it manually."
- **H6: an unattended automation/integration run overnight** — the timing (overnight, no human recollection) is itself evidence pointing away from a live human action and toward a scheduled or event-driven process.

H4 (sub-issue cascade) and H5 (workflow automation) are plausible secondary candidates worth ruling out quickly since they're cheap to check (steps 6–7) and would fully explain the behavior with zero GitHub involvement at all — which would mean the "PR still draft" fact is a red herring rather than a contradiction.

I would **not** conclude this was a deliberate/correct closure. The stated facts (PR open + draft) are strong evidence the work is not actually done, regardless of which mechanism flipped the status.

---

## 4. Recommended next steps

**Immediate (restore accurate state):**
1. Move PLAT-77 back to "In Progress" (or whatever state accurately reflects reality) now — don't leave the tracker showing "Done" while investigation is pending, since that's actively misleading anyone else looking at the board/roadmap.
2. Leave a comment on the issue documenting: the anomaly, the timestamp, and "under investigation" — so the history is transparent and the next person doesn't re-trigger confusion.
3. Do **not** just flip the status back and move on without doing step 1 of the checklist (pulling the activity log) — if this was caused by a live automation/integration bug, it will very likely recur on the next PR merge or the next scheduled run unless root-caused.

**Root-cause and fix:**
4. Run through the investigation checklist above (Section 2) to identify the actual trigger.
5. Once identified:
   - If **H1/H2** (wrong-issue keyword match): fix the mislabeled commit/PR reference where possible, and consider whether the team wants stricter conventions (e.g., requiring exact branch-name-based linking rather than free-text keyword parsing) to reduce future misfires.
   - If **H5/H6** (automation/integration): fix or disable the offending rule/script, and audit what else it may have touched (other issues could be silently wrong too — this shouldn't be assumed to be an isolated, one-issue incident until checked).
   - If **H4** (sub-issue cascade): decide whether that auto-complete behavior is actually wanted, since it can silently mark a parent Done based on sub-issue state alone, independent of the PR that's supposed to represent the "real" work.
   - If **H7** (human bulk-edit): no system fix needed, just team awareness — but confirm this only after checking the audit log, not by assumption.
6. **Audit for blast radius:** if the cause was systemic (integration misconfiguration, automation rule, or script), check whether other issues were affected by the same overnight event/run, not just PLAT-77 — a single symptom report is often the visible tip of a broader sync problem.
7. **Consider a guardrail:** e.g., a Linear workflow rule or a lightweight check that flags/alerts when an issue moves to Done while its only linked PR is still open/draft — this exact mismatch is detectable and would catch this class of problem going forward without requiring someone to notice it by chance.

---

## 5. Open questions for the team (to resolve which hypothesis is correct)

- Does PLAT-77 have any sub-issues, and were any of them closed overnight?
- Is there more than one PR/branch linked to PLAT-77 in Linear's attachment panel?
- Did any *other* PR merge overnight that might reference PLAT-77 (or a similar-looking issue ID) in its title, description, or commit messages?
- Are there any scheduled jobs, Zapier/Make/n8n scenarios, or internal scripts with Linear API write access that run overnight?
- What does the Linear GitHub integration's state-mapping config actually say for "Done" — merge only, or something broader?
- Does the issue's Activity/History log attribute the change to a named human user, a bot/integration, or an API token?
