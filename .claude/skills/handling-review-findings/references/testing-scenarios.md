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
  via a single `AskUserQuestion` call carrying two questions (Q1: which enabled reviewer(s), multi-select;
  Q2: default or full review profile, single-select), then posts the matching trigger comment(s) per
  reviewer and ends its run without polling for the response.
- Devin is one of the reviewers offered in Question 1 — selecting either profile in Question 2 for
  Devin resolves to the same posted string, since its `default_review_trigger` and
  `full_review_trigger` are identical; this needs no special case in either question's logic.
- A reviewer has `enabled: false` in `review_findings_reviewers` — it never appears as an option in
  Question 1.
- The user selects "No further round for now" in Question 1 (alone, or alongside a reviewer option) —
  Question 2's answer is ignored entirely and no trigger comment is posted, regardless of what Question
  2 says.
- Both trigger-ask questions are answered, but the commit(s) meant to be reviewed this round are still
  local-only — `git rev-parse HEAD` doesn't match the PR's freshly re-fetched `headRefOid`. No trigger
  comment gets posted; the run stops and tells the user which commit(s) are unpushed, rather than
  treating "the AskUserQuestion was answered" as license to post.
- Both trigger-ask questions are answered and the local commit is pushed, but the PR is currently a
  draft (or closed) — no trigger comment gets posted regardless of how the questions were answered.
- Round 2's trigger-ask already happened earlier in the conversation; round 2 is now triaged and the
  budget allows round 3 — the skill reuses the earlier answer and posts round 3's trigger comment
  without asking again.
- A fresh session (no memory of an earlier trigger-ask answer) is asked to triage what turns out to be
  round 3 — it asks the reviewer/mode question again, since there's no persisted state to reuse.
- A reviewer entry's `name` field is malformed (contains uppercase, a regex metacharacter, or a path
  separator, e.g. `name: "co.dex"` or `name: "co/dex"`) — that entry is excluded from the trigger-ask
  entirely, before its trigger string is ever checked, rather than being substituted into the
  handle-token regex or a scratchpad filename unvalidated.
- Round 1 comes back clean (no findings at all, or only declined/filed ones) — no fix-driven push
  happens, so the round never closes under `references/round-and-dedup-rules.md`'s fix-driven-push
  definition. The trigger-ask's budget check still correctly treats this as one triggered cycle (via
  the re-derived, marker-based batch count), not as "round 1 still incomplete," and doesn't re-offer a
  trigger-ask indefinitely for the same still-open round.
- `codex-review-recovery` has posted its own `@codex review` retry comment on this same PR (a stuck-check
  recovery, not a proactive round trigger) — the triggered-cycle count does not count it, since it
  carries no `handling-review-findings-trigger` marker, even though its body text is byte-identical to
  what this skill's own Codex trigger would post.
- The user selects two reviewers (e.g. Codex and Devin) in one Question 1/Question 2 answer — both
  resulting comments share the same `<batch-id>` marker, and the triggered-cycle count advances by
  exactly 1 for this decision, never by 2.
- The current triggered-cycle count is below `review_findings_min_rounds` (e.g. `min_rounds: 2` and only
  round 1's automatic trigger has happened so far) — Question 1 offers only the validated reviewer
  options, with no "No further round for now" option at all, so the floor can't be defeated by selecting
  it.
- `review_findings_max_rounds` is reached — the skill's report states plainly that no further round
  will be triggered, and SKILL.md's Workflow step 8 is skipped entirely (not silently treated as "no
  more findings").
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
- A tracked `.claude/git-kit.local.json` sets a reviewer's `enabled: false` — the whole-array
  trust-boundary resolution at Settings-read time uses the tracked `git-kit.settings.json` array
  instead, so that reviewer is still offered in Question 1, never silently suppressed by the tracked
  local file's claim.
- A tracked `.claude/git-kit.local.json` sets `review_findings_severity_gate: true`,
  `review_findings_generate_issues: true`, or a `review_findings_max_rounds` lower than the tracked
  default — each of these three scalar fields falls back to the tracked default too, the same as
  `enabled`, and the run reports plainly which field(s) were discarded this way.
- A tracked `.claude/git-kit.local.json` deletes a reviewer entry from its own array, or sets
  `review_findings_reviewers: []` — the whole-array resolution means this has no effect; the tracked
  default's full roster is used regardless, rather than a per-entry join that would let a tracked file
  silently narrow the roster by omission.
- The trust-boundary check (`git ls-files --error-unmatch ":(top,literal).claude/git-kit.local.json"`) is
  run from a subdirectory of the repo, not the repo root — the anchored, glob-disabled pathspec still
  correctly reports the file as tracked; a bare relative pathspec would wrongly report "no match" and
  fail the boundary open.
- The `max_rounds`-th triggered batch is posted, and its own review comes back with findings — those
  findings are fixed through the normal Fix path even though 8a's triggered-cycle count already reads
  `max_rounds` by the time they're classified; they are not treated as post-budget just because the
  counter is already at the ceiling.
- A finding arrives from a human comment in a round *after* the round the `max_rounds`-th batch opened
  — this one is genuinely post-budget: fixed if `review_findings_generate_issues` is `false`, filed if
  `true`.
- 8c leaves exactly one reviewer surviving validation (the other two disabled or invalid) and the
  triggered-cycle count is below `min_rounds` — Question 1 offers that one reviewer plus "No further
  round for now" (2 options, satisfying `AskUserQuestion`'s minimum), but selecting the stop option
  doesn't silently end the run below the floor; it reports the floor isn't met and stops for the user to
  confirm the one reviewer or fix the configuration.
- 8c leaves zero reviewers surviving validation — 8b's `AskUserQuestion` is skipped entirely; the run
  reports plainly that no reviewer is available to trigger, naming each excluded entry and 8c's reason.
- A human reviewer leaves an ordinary comment with no severity label or badge at all (e.g. "this looks
  wrong, please check the null case") — severity is classified from what the described defect actually
  warrants (`references/round-and-dedup-rules.md`'s Hard Cap section), not left undefined; if that
  content-based judgment is itself uncertain, the finding defaults to Major rather than silently
  defaulting to Minor and risking a real Critical/Major finding bypassing the Hard Cap exception.

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
- [ ] The trigger-ask is always one `AskUserQuestion` call carrying two questions (reviewer multi-select,
      then review-profile single-select) — never a single combined question offering a default-vs-full
      pair per reviewer, and never two separate `AskUserQuestion` calls.
- [ ] Selecting "No further round for now" in Question 1 always overrides any other selection in that
      same question and skips Question 2's answer entirely — no trigger comment is posted regardless of
      what Question 2 says.
- [ ] Before posting any trigger comment, the PR's `state`/`isDraft`/`headRefOid` are re-fetched fresh
      (never reused from an earlier check) and `headRefOid` is compared against `git rev-parse HEAD` —
      a mismatch (local commit not yet pushed), a draft PR, or a non-`OPEN` state each independently
      blocks posting, and a completed `AskUserQuestion` answer is never treated as itself satisfying
      this precondition.
- [ ] A reviewer with `enabled: false` never appears as a Question 1 option.
- [ ] A reviewer whose `name` field fails `^[a-z][a-z0-9_-]{0,31}$` is excluded from the trigger-ask
      before its trigger string is checked at all — its `name` is never substituted into the
      handle-token regex or a scratchpad filename unvalidated.
- [ ] The triggered-cycle count Workflow step 8 compares against `min_rounds`/`max_rounds` is derived
      from re-fetched state (1 for round 1's automatic trigger, plus the number of distinct
      `handling-review-findings-trigger:<batch-id>` markers found in the current comment list) — never
      from the fix-driven-push "round" definition, which would never close (and never let the count
      reach `max_rounds`) for a cycle that comes back clean or produces only declined/filed findings.
- [ ] A comment whose body matches a configured trigger string but carries no
      `handling-review-findings-trigger` marker (a `codex-review-recovery` retry, a coincidentally
      identical human comment) is never counted toward the triggered-cycle count.
- [ ] Every comment posted for one Question 1/Question 2 decision shares the same `<batch-id>`, so a
      multi-reviewer selection always advances the triggered-cycle count by exactly 1, never by the
      number of reviewers selected.
- [ ] When the current triggered-cycle count is below `review_findings_min_rounds`, Question 1 never
      offers a "No further round for now" option — only when the count already meets or exceeds
      `min_rounds` does that option appear.
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
- [ ] The trust boundary is resolved once at Settings-read time (never deferred into 8c, never
      re-derived per field) using a repo-root-anchored `git ls-files` pathspec, and applies as a group to
      all four protected fields (`severity_gate`, `generate_issues`, `max_rounds`-lower-than-default, and
      the *entire* `review_findings_reviewers` array) — never a per-reviewer or per-field join that could
      let a tracked local file narrow the roster or weaken one field while the others stay protected. The
      run reports plainly, once, which field(s) were discarded this way.
- [ ] A finding produced by the review that the `max_rounds`-th triggered batch itself triggered is
      fixed normally, never routed to the Issue/generate-issues path merely because 8a's aggregate count
      already reads `max_rounds` when it's classified — only a finding from a genuinely later round is
      treated as post-budget.
- [ ] When 8c leaves exactly one validated reviewer, Question 1 includes the stop option regardless of
      `min_rounds` status (to satisfy `AskUserQuestion`'s 2-option minimum), but below the floor
      selecting it reports the unmet floor and stops rather than silently ending the run.
- [ ] When 8c leaves zero validated reviewers, 8b's `AskUserQuestion` is never constructed with an
      empty or single-item options array — the run reports the configuration gap instead.
- [ ] A finding with no reviewer-stated severity label at all is never left unclassified — it's judged
      from the described defect's actual content, and defaults to Major (never Minor) when that
      judgment is itself uncertain.
