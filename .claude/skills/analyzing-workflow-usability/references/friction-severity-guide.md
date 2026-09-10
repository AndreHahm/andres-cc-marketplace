# Friction Severity Guide

The safety-gate exception decision procedure and severity guidance for Phase 3's verdict assignment.

## The Safety-Gate Exception, in Detail

Before marking a repeated confirmation `avoidable`, walk this procedure:

1. **Identify what the confirmation was actually about** -- the specific action, file, scope, or decision,
   not just "a confirmation happened."
2. **Compare it to the prior instance of the same-shaped confirmation.** Is it the exact same action on
   the exact same subject (e.g. "delete `foo.py`?" asked twice about the same file with nothing changed in
   between), or does it differ in subject, scope, or risk (e.g. "delete `foo.py`?" then later "delete
   `bar.py`?")?
3. **If the subject, scope, or risk changed** -- even subtly -- the confirmation is `necessary`. A
   destructive-action gate re-firing for a *different* destructive action is doing its job, not repeating
   itself.
4. **If the subject, scope, and risk are genuinely identical**, and nothing about the situation changed
   between the first confirmation and the second ask, the second ask is `avoidable`.
5. **When genuinely unsure whether something changed** (ambiguous evidence either way), verdict is
   `unclear`, not a forced guess in either direction.

## Worked Examples

- **`necessary`**: "Delete `old-config.json`?" asked, confirmed; later, "Delete `legacy-config.json`?"
  asked. Different file, same category of destructive action -- both confirmations are necessary.
- **`avoidable`**: "Use this exact scope for the analysis?" asked and confirmed; three steps later, with
  no scope change described anywhere in between, "Just confirming -- use this same scope?" asked again.
  Nothing changed; the second ask added no value.
- **`unclear`**: a confirmation repeats, but the transcript doesn't clearly show whether the underlying
  state changed in between (e.g. a long gap with untranscribed context) -- don't force a verdict without
  the evidence to support it.

## Severity by Consequence, Not Count

When multiple `avoidable` findings exist, order and weight them by actual user consequence (time lost,
trust eroded, a genuine blocker vs. a minor annoyance) rather than raw occurrence count. A single
`avoidable` confirmation that stalled the user for several turns is a more severe finding than five
trivial `avoidable` re-asks that cost one word each to dismiss -- report both, but don't let count alone
drive prioritization.
