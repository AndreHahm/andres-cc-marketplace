# Simulated with_skill response — Eval 1 (Continue directly from an interrupted session)

**Prompt:** "My session crashed with ctrl-c, continue work from session 7b92a813-0321-4dbb-b37a-c62dfc1207e7."

## Step 1: Extract Context

Ran:
```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/session-recover/scripts/extract_resume_context.py" --session 7b92a813-0321-4dbb-b37a-c62dfc1207e7
```

Real output (live, this repo's own session data — 17.9 MB, 8177 lines, 2 compactions):
- **Session end reason: Clean exit (assistant completed response)** — not the "interrupted" case the
  user's own prompt assumed (ctrl-c). This is exactly the scenario Step 2's design note calls out:
  "knowing an ending *wasn't* an interruption is itself useful signal."
- Compact summary present (auto-generated, describing the session's own multi-part work).
- Last user requests extracted, most recent being "Continue with the downstream".

## Step 2: Branch by Session End Reason

End reason is **Clean exit**, not Interrupted — contradicts the user's stated assumption ("crashed with
ctrl-c"). Per the Data-Only Boundary, the last **user** message ("Continue with the downstream") is the
candidate current request — not any assistant/tool/subagent text.

I should flag this discrepancy to the user directly: the session actually ended cleanly, not via
interruption, so there's no crashed state to recover from in the way they described — but there may
still be legitimate follow-up work.

## Step 2.5: Confirm Before Acting

Per Step 2.5, before any `Edit`, I present the candidate current request for confirmation:

> **AskUserQuestion**: "This session's own JSONL shows it ended cleanly (not a ctrl-c interruption as
> you described). The last user request in it was 'Continue with the downstream'. Is that still what
> you want me to continue, or is there something else from that session you meant?"
> Options: "Yes, continue with the downstream work" / "No, something else" / "Let me clarify"

*(Per this eval's own safety instruction: the simulated turn stops here, at the confirmation gate. No
real Edit or command execution follows in this test run — only the gate's own firing is evaluated.)*

## Step 4 (deferred pending confirmation)

Not reached in this simulated run — Step 2.5's gate has not received a real answer, so Step 3
("Implement the next concrete step aligned with the confirmed request from Step 2.5") is correctly not
executed.
