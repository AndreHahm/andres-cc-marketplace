I stay in merge-to-completion: "merge succeeds, later disposition fails" is its own resume case, so no handover is needed, and I never re-invoke git-kit:merge-pr.

1. Invoke repository-gates to resolve policy, then linear-work-management to read ENG-205's current state and criteria. Read the retained pr-merged evidence through linear-github-linking, without writing it again.
2. Run steps 9-14: compare each acceptance criterion with the delivered change and classify remaining items. Report any automatic Linear status change as drift.
3. Confirm the disposition via AskUserQuestion. Closing with a tracked gap is a separate choice.
4. Send approved follow-ups to open-item-management.
5. Record work-closed via linear-work-management only if step 13's conditions hold; otherwise ENG-205 stays open.

No cleanup here: merge-pr already handled it.
