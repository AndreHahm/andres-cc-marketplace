# Simulated with_skill response — Eval 2 (Correctly redirects an in-place continuation request)

**Prompt:** "My session just crashed with ctrl-c, help me continue working on it right here in this
conversation."

## Response

Matches the skill's own When NOT to Use bullet directly: "Wants to continue the work directly in *this*
conversation rather than receive a portable document → use `session-recover` instead."

Declines to synthesize a recovery document; redirects:

> This isn't `session-resume`'s job — it produces a portable document for review or handoff elsewhere.
> For continuing directly in this conversation after an interruption, use `session-recover` instead.

No script run, no document synthesized.
