# Usability Dimensions

The eight dimensions `analyzing-workflow-usability`'s Phase 2 inventories friction against.

1. **Discoverability** -- could the user find the right capability/skill/option without already knowing it
   existed? A user who had to ask "what can you do" or stumbled onto the right approach by trial and error
   is evidence against discoverability; a user who invoked the right thing directly, or was offered it
   proactively, is evidence for it.
2. **Repeated context** -- did the user have to re-explain something they'd already stated earlier in the
   same scope? Distinct from a legitimate scope change -- re-stating genuinely new information isn't
   repeated context.
3. **Confirmation burden** -- how many confirmations did the user have to answer, and did each one clear
   the safety-gate exception (Phase 3)? A burden finding here should cite the specific confirmations, not
   just a count.
4. **Cognitive load** -- did the user have to hold a lot of state in their head to follow what was
   happening (many simultaneous options, an unclear multi-step plan, jargon without explanation)?
5. **Correction burden** -- how many times did the user have to correct course, and what did each
   correction actually cost them (see Phase 3's "weight by consequence, not count")?
6. **Time-to-first-useful-result** -- how long, in interaction steps (not necessarily wall-clock time),
   before the user got something they could actually act on or evaluate?
7. **Readability** -- was output structured so a human could actually parse it (clear headings, scannable
   structure, no wall-of-text dump), or did the user have to do extra work to extract the useful part?
8. **Actionability** -- did output tell the user (or a downstream reader) what to do next, or did it stop
   at description without a clear next step?

## Scope Note

These dimensions describe the *interaction*, not the underlying work's correctness -- a technically
correct answer delivered with high friction is still a usability finding; a friction-free interaction that
produced a wrong answer is a correctness finding for a different skill (`analyzing-session-outcomes`,
`analyzing-verification-effectiveness`), not this one.
