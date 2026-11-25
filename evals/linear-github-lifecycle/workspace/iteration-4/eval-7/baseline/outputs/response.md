I stop pr-to-linear here and hand over to linear-github-lifecycle via Skill(linear-github-lifecycle), passing ENG-205, PR 45, "in review", goal: merged.

Why: the request is to resume an interrupted end-to-end run through merge. pr-to-linear covers only the review-reflection stage; its text sends merging to merge-to-completion and grants neither that skill nor the lifecycle skill. The document does not name linear-github-lifecycle as the resume owner; I infer that from its name in the session's skill list. The orchestrator should re-read the actual state and choose the stage, likely pr-to-linear (with git-kit:handling-review-findings), then merge-to-completion.

I run no triage, ready marking, Linear write or merge now; "carry on until merged" does not waive the confirmation gates.
