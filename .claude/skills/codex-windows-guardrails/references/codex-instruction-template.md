# Codex Instruction Template

**This is a request the model could ignore, not a technical enforcement mechanism.** Nothing on this
session's side intercepts what Codex's own agent loop does once `codex exec` starts running with
`danger-full-access` — there is no pre-execution interception point (see
`references/hooks-sync-investigation.md`). This text asks Codex to self-restrict; it does not force
it to. State this limitation plainly wherever this template is referenced — never present its
presence in a dispatched prompt as equivalent to a real command allowlist.

## Source of truth

`assets/dangerous-command-instructions.txt` — `scripts/guarded-dispatch.mjs` reads this file
directly and inserts it into the prompt's `<guardrail_instructions>` block (see
`references/dispatch.md`). This document explains it; it is not a second copy of the text, so the
two can't drift out of sync with each other.

## Where the blocked-category list came from

The categories in that text file are reused verbatim from the original `WINDOWS_GUARDRAILS.md`
concept's "Blocked categories include, at minimum" list — not re-derived. That document imagined
this list enforced by a runtime hook; this skill enforces it only as much as an instructed model
chooses to follow it. The text itself leads with the required posture (stay read-only/inspection-only)
before mentioning the underlying capability, reordered during Self-Review from an earlier draft that
led with "you have unrestricted access" — technically accurate either way, but leading with the
restriction reads less like an invitation.
