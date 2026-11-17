# Routing answer

## 1. "verify the rollback step in docs/deploy-plan.md before I run it" -> codex-verify

The user asks to verify one step of an existing document file. The deciding text:

- codex-verify description: "A plan, document or single plan step the user asks to have verified stays here, even a critical step Claude will execute later."
- codex-verify, When to Use: "One step of a plan the user asks to have verified ("verify step 3 of plan.md"), critical or not, even when Claude will execute it later. The whole document is still verified and the verdict is document-wide, so another step's problem can fail it; step-scoped verification is issue #731."

Why not consulting-decision-model: codex-verify sends it only "Claude's own check, with no user request to verify it, of one critical, security-relevant or uncertain step it is about to execute". Here the user asked for the check, and the user will run the step ("before I run it"), not Claude.
Why not codex-peer-review: "An existing written plan or document file to check → `codex-verify`."
Why not cross-model-review: "an existing plan or document file → `codex-verify`. This skill reviews a diff."

Caveat from the skill text: the verdict covers the whole of docs/deploy-plan.md, not only the rollback step, so a problem in another step can fail it.

## 2. "cross-model review this diff before I open the PR" -> cross-model-review

The deciding text:

- cross-model-review, When to Use: "Before a PR is created (draft or ready-to-merge), or before a draft PR is flipped to ready ... Also for an explicit "adversarial review," "cross-model review," or "second-opinion review" request on the working diff."
- cross-model-review, Testing & Validation (activates on): "cross-model review this diff" / "second-opinion review before I create the PR".
- codex-verify, Testing & Validation (does NOT activate on): ""cross-model review this diff before I open the PR" → git-kit's `cross-model-review`".

Why not codex-peer-review: "A second opinion on the working diff before a PR is created or a draft is flipped to ready → git-kit's `cross-model-review`. This skill validates a position, not a diff."
Why not consulting-decision-model: cross-model-review "reviews a diff, never one decision."
