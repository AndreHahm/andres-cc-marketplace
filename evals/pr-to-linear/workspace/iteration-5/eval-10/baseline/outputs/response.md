I do not record `pr-ready` for either SHA: it is valid only for the head confirmed in step 5 (a1b2), and c3d4 was never verified. I tell the user the head moved after confirmation, and that the PR is already non-draft.

Then I re-verify from step 5: re-read draft state, SHA, required checks, reviews, description and Linear link. The new commit can have brought new inline comments I cannot read, so I ask via `AskUserQuestion` before re-dispatching `git-kit:handling-review-findings` (it can fix, push, reply, resolve), whatever was approved earlier. On no or no answer, I stop, recording nothing.

On yes and clean: revalidate Linear (6), reconfirm (7), skip rerunning `gh pr ready`, re-read; if the SHA still matches, record it with manual provider. No Linear status move meanwhile.
