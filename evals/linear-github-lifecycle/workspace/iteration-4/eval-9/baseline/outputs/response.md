I run this skill's own procedure for ENG-205. I don't re-invoke linear-github-lifecycle: it dispatched me for exactly this phase and owns the rest.

First, invoke `linear-work-management` to read the Issue and confirm readiness; stop and report if criteria are missing or contradictory. Then `repository-gates` (policy; git-kit is the provider), then `linear-github-linking` (existing branch/commit/PR, so no duplicate).

Next, show the summary and proposed branch via `AskUserQuestion`; "all the way to merge" isn't that approval. Once confirmed, invoke `git-kit:starting-work`, read back the actual branch/worktree and base, record `work-started` via `linear-github-linking`, then set Started via `linear-work-management`.

Finally, report back so the running linear-github-lifecycle continues. I don't commit, open a PR or merge.
