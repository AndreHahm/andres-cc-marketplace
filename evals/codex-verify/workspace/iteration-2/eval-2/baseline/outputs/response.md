# Routing answer

## 1. "verify the rollback step in docs/deploy-plan.md before I run it" -> codex-verify

The user asks to verify one step of an existing plan file. codex-verify keeps this case even though the step is critical and will be executed later:

- codex-verify description: "A plan, document or single plan step the user asks to have verified stays here, even a critical step Claude will execute later. Claude's own check of one critical, security-relevant or uncertain step it is about to execute, with no such request, goes to consulting-decision-model instead."
- codex-verify, When to Use: "One step of a plan the user asks to have verified ("verify step 3 of plan.md"), critical or not, even when Claude will execute it later. The whole document is still verified and the verdict is document-wide, so another step's problem can fail it; step-scoped verification is issue #731."
- consulting-decision-model does not apply here. Per codex-verify, it covers only "Claude's own check, with no user request to verify it", and that check "runs when Claude executes the step, separately from any verification the user asked for here."
- codex-peer-review does not apply. Its When NOT to Use says: "An existing written plan or document file to check → `codex-verify`."

Caveat from the skill text: the verdict covers the whole document, so a problem in another step can fail it.

## 2. "cross-model review this diff before I open the PR" -> cross-model-review

- cross-model-review description: "Reviews the current diff adversarially across two model vendors before a PR is created (draft or ready) ... Use for an adversarial review, a cross-model or second-opinion review, a pre-PR gate, or high-confidence findings before opening or readying a PR."
- cross-model-review, When to Use: "Also for an explicit "adversarial review," "cross-model review," or "second-opinion review" request on the working diff."
- cross-model-review, Testing & Validation lists the activation phrase "cross-model review this diff" / "second-opinion review before I create the PR".
- The other skills do not fit. codex-verify says "Code review → `/codex-kit:cdx-review`", and consulting-decision-model covers "one action, no diff" ("This skill reviews a diff, never one decision.").
