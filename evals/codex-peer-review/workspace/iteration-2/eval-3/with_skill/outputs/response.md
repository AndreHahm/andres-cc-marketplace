# Which skill checks a self-chosen database migration before it runs?

Running a database migration that Claude chose itself is one critical action Claude is about to execute. Nobody asked for a review, so codex-peer-review does not apply here. Its text says it is "Not a proactive/automatic trigger", and it lists "Proactively, with no explicit request: this skill deliberately has no automatic trigger" under When NOT to Use.

## (a) decision-kit is installed

**Skill:** decision-kit's `consulting-decision-model`.

The deciding sentences:

- Description: "For one critical, security-relevant or uncertain action or choice Claude is about to execute, use decision-kit's consulting-decision-model instead, when decision-kit is installed."
- When NOT to Use: "One critical, security-relevant or uncertain action or choice Claude is about to execute → decision-kit's `consulting-decision-model`, when decision-kit is installed."

## (b) decision-kit is not installed

**Skill:** none. No installed skill checks the action, and codex-peer-review does not take it on as a fallback.

The deciding sentence (When NOT to Use): "Without it, no installed skill makes that check, and this skill still does not take it on."

The Testing & Validation section says the same: "(without it, no installed skill makes that check)".
