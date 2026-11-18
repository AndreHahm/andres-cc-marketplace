Plan for "merge pr 903" in ship mode (no tools run; only the two profile files were read).

**Decision: I would not merge yet.** The Security workflow's secretlint job failed and nobody has triaged it. ship.md says:
- "It runs on every PR but is not a required check, so GitHub lets the merge through on a failure: do not. Stop until the failure is triaged, either the secret removed (and rotated) or the finding shown to be a false positive, and say which."
- "Do not merge over a failed secretlint result that has not been triaged."

**Step by step:**
1. Re-read the PR's current state before doing anything, because the state given to me may be stale. The tool calls would be `gh pr checks 903` and the secretlint job log, read only.
2. Reply in ship.md's output structure:
   - **What's shipping:** PR #903.
   - **Destination:** a merge into main.
   - **Pre-ship checks:** approved; all required checks green; no outside company, product or repository names added, so the external-reference check doesn't apply; **secretlint FAILED**, with one possible credential in `config/settings.example.json`, not yet triaged.
   - **Confirmation:** blocked.
3. Ask with AskUserQuestion, per generic.md's "Use `AskUserQuestion` for any choice or proceed gate". The options would be "Inspect the flagged line to decide if it's a false positive" or "Treat it as real: remove the secret and rotate it".
4. Only after the finding is triaged, and I've said which way it went, dispatch `Skill(merge-pr)`. I would never use a raw `gh pr merge` ("Merge: `merge-pr` ... never a raw `gh pr merge`"). I would also ask you to confirm the merge itself ("confirm that specific action even if a similar one was approved earlier").
