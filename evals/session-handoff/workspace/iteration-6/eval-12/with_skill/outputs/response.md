**Result:** I would write `state: pr-draft` and `context_mode: review`. I would not override `context_mode`.

1. **Pick `state` from the Step 2 item 5 table.** The skill says to "set the frontmatter's `state` to where the work stands, judged from what this session knows about the next step."
   - The matching row is: "`pr-draft` | A draft PR is open | `review`". PR #904 is still a draft, so this row applies.
   - `ready-to-merge` does not fit, even though the checks are green and there are no findings. Its row requires: "The next step is `merge-pr` and nothing else is left before it: **the PR is not a draft**…" Here the PR is a draft, and the next step is to flip it to ready. Merging comes after that, so "nothing else is left" is not true.
   - `in-review` does not fit either. Its row covers "The next step opens the PR, or a non-draft PR is open…" The PR is already open and it is a draft.
   - The tie-breaker "When unsure between `in-review` and `ready-to-merge`, choose `in-review`" does not come into play. The draft row matches directly, and it gives the same mode anyway.

2. **Take `context_mode` from the same row.** The skill says "then set `context_mode` … from the same row". For `pr-draft` that is `review`.
   - I would not override it. The skill says "Override `context_mode` only with the reason stated in Important Context." Nothing here is configuration, permission or setup work. `ship` would be wrong too, because it only belongs to `ready-to-merge` and `ready-to-publish`.

3. **Put the plan in the body, not the frontmatter.**
   - Immediate Next Steps item 1: flip PR #904 from draft to ready for review. Item 2: merge it with `merge-pr`.
   - The Resume Card is filled last (item 6). It carries state `pr-draft`, next step 1 verbatim, the branch and PR #904, no blockers, and any standing user instructions.

4. **Validate at Step 3.** `validate_handoff.py` checks that `state` and `context_mode` are in the closed sets. Because there is no override, it reports no override note.
