# Simulated with_skill response — Eval 2 (Correctly redirects a portable-document request)

**Prompt:** "I want a portable recovery document for this session that I can hand to a different,
separate session later."

## Response

This request matches this skill's own "When NOT to Use" section directly: "Wants a portable recovery
**document** to hand off to a *different* session or share elsewhere, rather than continuing directly
here — use `session-resume` instead."

The request explicitly says "hand to a different, separate session later" — an unambiguous match for
that exclusion, recognizable from the user's message alone with no need to inspect any session data
first (there's no legitimate reason to run the extraction script for a request this skill is declining
outright).

**Declining and redirecting:**

> This isn't `session-recover`'s job — it continues work directly in *this* conversation rather than
> producing a portable document for a different session. For a context-recovery prompt you can hand to
> another session, use `session-resume` instead.

No script was run; no session data was gathered, since the request is out of scope before any of that
would matter.
