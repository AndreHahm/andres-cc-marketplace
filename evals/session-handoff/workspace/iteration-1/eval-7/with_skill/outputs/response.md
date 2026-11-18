`Context mode: review`

Reason: The skill allows `ship` only when every condition holds. Here one Codex finding is still untriaged, so the "no review findings are left to triage" condition fails, and the next step is to finish the review before merging, not `merge-pr` directly. The rule picks `review` whenever a PR is open and review or fix work may still be needed. If it were unclear between `review` and `ship`, the skill also says to choose `review`.
