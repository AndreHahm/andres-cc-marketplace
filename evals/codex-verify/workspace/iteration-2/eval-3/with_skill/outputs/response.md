# Which skill checks an unrequested force-push step (step 4 of docs/deploy-plan.md)

The scenario: Claude is about to execute step 4 (a force-push, which is critical and security-relevant), and the user did not ask for it to be verified. So codex-verify's "user asked to verify" route does not apply. Its own text sends this case elsewhere.

## (a) decision-kit installed: decision-kit's `consulting-decision-model`

From the description (frontmatter):

> "Claude's own check of one critical, security-relevant or uncertain step it is about to execute, with no such request, goes to decision-kit's consulting-decision-model instead, when decision-kit is installed."

From "When NOT to Use":

> "Claude's own check, with no user request to verify it, of one critical, security-relevant or uncertain step it is about to execute → decision-kit's `consulting-decision-model`, when decision-kit is installed. That check runs when Claude executes the step, separately from any verification the user asked for here."

## (b) decision-kit not installed: no skill, and codex-verify does not take it either

From "When NOT to Use":

> "Without decision-kit, no installed skill makes it, and this skill still does not."

From Testing & Validation:

> "... → decision-kit's `consulting-decision-model`, when decision-kit is installed (without it, no installed skill makes that check)."

## Why codex-verify does not apply in either case

codex-verify keeps a step only when the user asked for it to be verified: "A plan, document or single plan step the user asks to have verified stays here, even a critical step Claude will execute later." Nobody asked here, so this skill does not run. It also does not act as a fallback when decision-kit is missing.
