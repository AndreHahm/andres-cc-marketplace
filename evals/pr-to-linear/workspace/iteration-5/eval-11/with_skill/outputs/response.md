Next: ask via `AskUserQuestion`, before touching Linear: "Move ENG-230 (PR #77) to In Review?" with options to move it or leave the status unchanged.

Why: the approved workflow calls for the move, so step 10 applies. But that policy only makes the step eligible; a policy value never answers a question the skill asks. Nor do the recorded pr-ready or earlier confirmations (steps 1.5, 7, 8). The status move is listed as approval-required in its own right.

On yes: make the move via `linear-work-management`, then report the result. If ENG-230 turns out to be already In Review through native automation, that is drift: preserve it and report it for `linear-github-reconciliation`. On no, or no answer: leave the status unchanged and report that; pr-ready stays recorded.
