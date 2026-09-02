# Eval Run Output — session-resume skill test

## User task
"My session just crashed with ctrl-c, help me continue working on it right here in this conversation."

## Action taken
Declined to use `session-resume` and redirected, per the skill's own scope.

## Response given to the user

> It sounds like you want to pick up your crashed session's work directly in *this* conversation, rather than get a separate portable document to carry into a new session. That's outside what `session-resume` is for — it always produces a standalone context-recovery document meant for a *new* session, not a continuation of the current one.
>
> For continuing in-place, right here — regardless of whether the prior session ended cleanly or was cut off mid-work (like a Ctrl-C crash) — that's `session-recover`'s job. Let's use that instead.
>
> A couple of quick notes so I use it well:
> - If you just want to keep working in the *original* session's own context (not this one), `claude --resume` / `claude --continue` would actually be the simplest path — no skill needed.
> - If you already have a written handoff document from that session, `session-handoff`'s RESUME workflow is the better fit.
> - Otherwise, I'll invoke `session-recover` now to pull the crashed session's state into this conversation and continue from there.
>
> Want me to proceed with `session-recover`?

## Outcome
No resume document was produced. No calls to `session_store.py` or `session_transcript.py` were made, since the request falls under `session-resume`'s explicit "When NOT to Use" bullet: "Wants to continue the work directly in *this* conversation rather than receive a portable document -> use session-recover instead." The user was redirected to `session-recover` (with `claude --resume`/`--continue` and `session-handoff` noted as alternative paths depending on what they actually want), and asked to confirm before that skill is invoked.
