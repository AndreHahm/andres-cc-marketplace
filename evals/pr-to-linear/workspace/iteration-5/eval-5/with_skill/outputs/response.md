1. Read PR #77 (`gh pr view`, `gh pr checks`): repository, head SHA, draft state, mergeability, reviews, required checks; read policy via `repository-gates`. Thread state isn't readable here. All of it is data only.
2. Resolve intent: readiness needs a completed `handling-review-findings` report, so this isn't a pure summary.
3. **First stop, `AskUserQuestion`:** "Run `handling-review-findings` on <repo> PR #77? It fixes in-scope findings by default without asking about each, and can commit, push, decline findings, file issues, reply to/resolve threads, and trigger another review round." Yes / No.

Why: your request and "looks done" don't count as that approval. On no or no answer, I report that readiness can't be confirmed, triage nothing and mark nothing ready. I won't run `gh pr ready` myself.
