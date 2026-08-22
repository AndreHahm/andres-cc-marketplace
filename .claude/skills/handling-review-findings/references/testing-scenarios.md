# Testing Scenarios and Quality Gates

## Named edge-case scenarios

- Two reviewers (e.g. Codex, Devin) finish at very different times against the same head SHA, with no
  fix-driven push between their two arrivals — both sets of findings belong to the same round.
- A finding is re-raised in a later round on the same file+line, but describes a genuinely different
  defect than the one already triaged there — dedup must not collapse it into the earlier finding.
- A round-1/2 fix is applied and pushed, but its own verification fails — the thread is never
  replied-to or resolved off that push; the finding stays open in the same round.
- An issue is filed with nothing else to commit in that round — the resulting commit is correctly
  labeled documentation-only and does not open a new round window even though the head SHA changed.
- A human reviewer has an active `CHANGES_REQUESTED` review alongside an otherwise-fully-triaged round
  — the workflow's own report never implies the PR is mergeable; that's `merge-pr`'s call.
- A Critical finding first appears in round 3, and none of the three named exceptions apply to it — it
  gets **fixed** like any other round-3 finding (the old automatic round-3-becomes-an-issue behavior no
  longer applies); if it instead matches a named exception (e.g. it's genuinely out of the PR's scope)
  and is filed, step 7 always surfaces it as a named merge-blocking risk requiring a separate
  `AskUserQuestion` acceptance, never folded into the routine fixed/filed/declined report alone.
- A finding arrives after `review_findings_max_rounds` is already exhausted, with
  `review_findings_generate_issues: false` (default) — it still gets fixed, not filed, even though this
  skill has stopped proactively triggering further rounds.
- Same as above, but `review_findings_generate_issues: true` — the finding is filed as an issue instead
  of forcing another round; if it's Critical/Major, the Hard Cap `AskUserQuestion` still fires before
  any merge discussion.
- A finding is flagged as concerning a component/plugin outside the PR's own changed scope (exception 2)
  — filed as an issue in round 1, without ever being attempted as a fix, regardless of round budget.
- The user explicitly says "just file that one, don't fix it now" for a specific finding (exception 1)
  — filed as an issue even though it's well within the round budget and easily fixable.
- Round 1 is triaged and fully handled; the round budget allows another round — the skill asks once,
  via `AskUserQuestion`, which enabled reviewer(s) and mode to trigger next, then posts the matching
  trigger comment(s) and ends its run without polling for the response.
- Devin is one of the reviewers offered in the trigger-ask — its option shows no default/full
  distinction, since `default_review_trigger` and `full_review_trigger` resolve to the same string.
- A reviewer has `enabled: false` in `review_findings_reviewers` — it never appears as an option in the
  trigger-ask.
- Round 2's trigger-ask already happened earlier in the conversation; round 2 is now triaged and the
  budget allows round 3 — the skill reuses the earlier answer and posts round 3's trigger comment
  without asking again.
- A fresh session (no memory of an earlier trigger-ask answer) is asked to triage what turns out to be
  round 3 — it asks the reviewer/mode question again, since there's no persisted state to reuse.
- `review_findings_max_rounds` is reached — the skill's report states plainly that no further round
  will be triggered, and Workflow step 8 is skipped entirely (not silently treated as "no more
  findings").
- `review_findings_severity_gate: true`, a Minor/nit finding in round 1, nobody asked for it explicitly
  — declined (reply only), never fixed, never filed.
- `review_findings_severity_gate: true`, same Minor/nit finding, but the user explicitly asks for it to
  be fixed anyway — the explicit instruction wins; it's fixed, not declined.
- A `security-reviewer` pass runs before round 2's fix is pushed and finds a new Critical issue — fixed
  within round 2, not treated as opening round 3.
- Two reviewers independently flag the same underlying defect, which matches the too-large-for-session
  exception — one issue is filed, not two; both threads get replied-to pointing at the same issue
  number. Round-agnostic: the exception applies in round 1 exactly as it would in round 3, since it's
  never gated on round budget.

## Quality gates

- [ ] A round is counted correctly per `references/round-and-dedup-rules.md` — a pre-push
      `security-reviewer` pass never advances the counter, and neither does a rebase or an unrelated
      commit landing on the same branch; only a fix-driven push advances it.
- [ ] Dedup correctly treats a same-file/same-or-overlapping-line finding as a repeat only after
      comparing actual content, never on location alone — and defaults to "new" whenever that
      comparison is uncertain.
- [ ] Round 1/2 findings are fixed, committed via `Skill(git-kit:commit)`, pushed, verified, and only
      then have their threads replied-to (citing the fixing commit SHA) and resolved — never resolved
      off an unverified push.
- [ ] A finding matching one of the three named exceptions (direct instruction, out-of-scope component,
      too large for this session) is never fixed in-session — each is filed via the
      draft-then-`gh issue create` pattern, using a non-closing reference, with its thread replied-to
      (issue number cited) but left unresolved.
- [ ] A round-3 (or any in-budget round) finding matching none of the three named exceptions gets
      **fixed**, never automatically filed just for arriving in a later round.
- [ ] The "too large for this session" exception follows the same Issue path regardless of which round
      it was raised in, and never consumes a round-budget slot.
- [ ] A post-`max_rounds` finding is fixed when `review_findings_generate_issues` is `false` (default)
      and filed when it's `true` — never the reverse.
- [ ] Workflow step 8's reviewer/mode `AskUserQuestion` fires at most once per conversation — a later
      round's trigger reuses the earlier answer rather than asking again, unless this is a fresh session
      with no memory of an earlier answer.
- [ ] A reviewer with `enabled: false` never appears as a trigger-ask option.
- [ ] Step 8 never fires at all once `review_findings_max_rounds` is reached.
- [ ] Step 8 never polls for the newly-triggered review's response — it ends this skill's run for the
      current round once the trigger comment(s) are posted.
- [ ] With `review_findings_severity_gate: true`, a Minor/nit finding is declined in every round unless
      explicitly requested — never fixed, never filed, by default.
- [ ] The disclosure step (Workflow step 7) always runs before any merge discussion, listing exactly
      what was fixed, filed, or declined.
- [ ] State (`gh pr checks`, `gh pr view`, the review-thread list) is always re-fetched immediately
      before any side-effecting action, never reused from an earlier check in the same conversation.
- [ ] A Critical/Major finding is never silently deferred-and-merged in any round — deferring one always
      requires a separate, explicit `AskUserQuestion` risk-acceptance, distinct from the routine
      fixed/filed/declined report.
- [ ] `merge-pr`'s own independent readiness gate is never treated as satisfied by this skill's own
      disclosure — a branch-protection-blocked merge stays blocked regardless of what this workflow
      classified a finding as.
- [ ] The reply-and-resolve marker (`gh-pr-review`) is always written immediately before the specific
      `gh api` reply/resolve call it authorizes, never earlier in the run.
- [ ] Every issue filed via the Issue path includes the full traceability payload (PR URL, head SHA,
      thread/comment URL, reviewer, severity) — never just the standard `github-issue-creator` template
      fields alone.
