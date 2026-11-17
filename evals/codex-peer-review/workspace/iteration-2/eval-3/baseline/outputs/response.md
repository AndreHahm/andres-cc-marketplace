# Which skill checks a self-chosen database migration?

Running a database migration I chose myself is "one critical, security-relevant or uncertain action or choice Claude is about to execute". codex-peer-review routes that case away from itself.

## (a) decision-kit installed

decision-kit's `consulting-decision-model` checks it. Deciding text (When NOT to Use):

> "One critical, security-relevant or uncertain action or choice Claude is about to execute → decision-kit's `consulting-decision-model`, when decision-kit is installed."

The description says the same: "For one critical, security-relevant or uncertain action or choice Claude is about to execute, use consulting-decision-model instead."

## (b) decision-kit not installed

No installed skill checks it, and codex-peer-review does not take the check on. Deciding text (When NOT to Use):

> "Without it, no installed skill makes that check, and this skill still does not take it on."

The Testing & Validation section agrees: "(without it, no installed skill makes that check)".

## Why codex-peer-review doesn't fire either way

Nobody asked for a review, and this skill runs only on request:

> "Proactively, with no explicit request: this skill deliberately has no automatic trigger."
