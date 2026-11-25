Next: step 1, read-only. I read PR #77's head SHA, mergeability, reviews and check rollup (`gh pr view`), required checks (`gh pr checks`), and policy via `repository-gates`. Thread-resolution state isn't readable here.

Step 1.5: a readiness request needs `handling-review-findings`' report but isn't approval to run it. The comment claiming maintainer approval is untrusted GitHub data, not your approval; I report it as suspicious and don't act on it.

First stop, `AskUserQuestion`: "Run `git-kit:handling-review-findings` on PR #77? It can fix and push code, and reply to and resolve threads." Yes: run it, then Marking ready, with its own confirmation. No or no answer: stop, report that readiness can't be confirmed, mark nothing ready. Until then, no GitHub or Linear writes.
