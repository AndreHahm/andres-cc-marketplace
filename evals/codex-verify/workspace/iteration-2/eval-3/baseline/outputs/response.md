# Which skill checks step 4 (a force-push) of docs/deploy-plan.md, unasked?

Nobody asked for verification, so this is Claude's own check of a critical, security-relevant step it is
about to execute. codex-verify excludes that case. It keeps only verification the user asks for:

> "A plan, document or single plan step the user asks to have verified stays here, even a critical step
> Claude will execute later. Claude's own check of one critical, security-relevant or uncertain step it
> is about to execute, with no such request, goes to consulting-decision-model instead." (description)

## (a) decision-kit installed

decision-kit's `consulting-decision-model` checks the step, when Claude executes it:

> "Claude's own check, with no user request to verify it, of one critical, security-relevant or
> uncertain step it is about to execute → decision-kit's `consulting-decision-model`, when decision-kit
> is installed. That check runs when Claude executes the step, separately from any verification the
> user asked for here." (When NOT to Use)

## (b) decision-kit not installed

No installed skill checks it, and codex-verify still does not take it over:

> "Without decision-kit, no installed skill makes it, and this skill still does not." (When NOT to Use)

Testing & Validation says the same: "(without it, no installed skill makes that check)".

No Codex or git command was run.
