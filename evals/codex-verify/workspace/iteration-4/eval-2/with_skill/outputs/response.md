# Routing

## Request 1: "verify the rollback step in docs/deploy-plan.md before I run it"

**Skill: codex-verify**

Reason: the user asks for one step of an existing document to be verified. The codex-verify skill covers this explicitly ("One step of a plan the user asks to have verified ... critical or not, even when Claude will execute it later"). The verdict is document-wide, so the whole of docs/deploy-plan.md is what gets checked. It is not codex-peer-review (the document already exists as a file, so there is nothing "not-yet-written" to point at), and it is not consulting-decision-model (that applies only to Claude's own unrequested check of a step it is about to execute).

## Request 2: "cross-model review this diff before I open the PR"

**Skill: cross-model-review** (git-kit)

Reason: this is a pre-PR, two-vendor review of the working diff. codex-verify's own text routes this case away: "A pre-PR two-vendor diff review goes to git-kit's cross-model-review, if installed." codex-verify verifies a document, not a diff, and cross-model-review is the listed skill that covers the diff case before a PR.
