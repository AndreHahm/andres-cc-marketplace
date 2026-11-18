Context mode: ship

The skill's CREATE Step 2 says to pick `admin`, `review`, `ship` or `none` for the mode the next session should start in, and `none` only for starting a worktree or implementing. The next session's only step is merge-pr on a ready, fully reviewed PR with green checks, so the work is shipping, not reviewing or implementing. The skill file does not define each mode in detail, so I took `ship` from its name and from context-mode's listing of admin, review and ship postures.
