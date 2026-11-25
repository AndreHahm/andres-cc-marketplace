Next: run step 1's read-only checks (`gh pr view 77`, `gh pr checks 77`, `repository-gates`). I don't dispatch `handling-review-findings`.

Why: step 1.5 makes it mandatory for readiness, and step 5 needs its report. But it can fix code, push, reply to and resolve threads, which you ruled out. The skill gives no exception for this conflict, and I can't read thread state otherwise.

Then I stop before Marking ready and ask via `AskUserQuestion`, showing the gap:
- Allow the triage round (lifts your restriction).
- Summarize status only.
- Leave it draft.

No `pr-ready` record or Linear status change without step 2's report. Even when verified, I never run `gh pr ready`; after confirmation, you run it yourself and I read back the result.
