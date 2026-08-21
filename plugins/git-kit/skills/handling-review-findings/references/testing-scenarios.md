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
- A Critical finding first appears in round 3 — it's filed as an issue (not fixed), but step 7 always
  surfaces it as a named merge-blocking risk requiring a separate `AskUserQuestion` acceptance, never
  folded into the routine fixed/filed/declined report alone.
- `review_findings_severity_gate: true`, a Minor/nit finding in round 1, nobody asked for it explicitly
  — declined (reply only), never fixed, never filed.
- `review_findings_severity_gate: true`, same Minor/nit finding, but the user explicitly asks for it to
  be fixed anyway — the explicit instruction wins; it's fixed, not declined.
- A `security-reviewer` pass runs before round 2's fix is pushed and finds a new Critical issue — fixed
  within round 2, not treated as opening round 3.
- Two reviewers independently flag the same defect in round 3 — one issue is filed, not two; both
  threads get replied-to pointing at the same issue number.

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
- [ ] Round 3+ findings are never fixed in-session — each is filed via the draft-then-`gh issue create`
      pattern, using a non-closing reference, with its thread replied-to (issue number cited) but left
      unresolved.
- [ ] A scope-deferred finding follows the same Issue path regardless of which round it was raised in,
      and never consumes a round-cap fix slot.
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
