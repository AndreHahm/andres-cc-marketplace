# Routing answer

## 1. "verify the rollback step in docs/deploy-plan.md before I run it" → `codex-verify`

The user asks to have one step of an existing document verified. That is codex-verify's case, not consulting-decision-model's. consulting-decision-model covers only Claude's own unasked check of a step Claude is about to execute. Here the user makes the request, and the user runs the step.

Deciding sentences:
- codex-verify description: "A plan, document or single plan step the user asks to have verified stays here, even a critical step Claude will execute later."
- codex-verify When to Use: "One step of a plan the user asks to have verified (\"verify step 3 of plan.md\"), critical or not, even when Claude will execute it later. The whole document is still verified and the verdict is document-wide, so another step's problem can fail it; step-scoped verification is issue #731."
- codex-verify When NOT to Use (rules out consulting-decision-model): "Claude's own check, with no user request to verify it, of one critical, security-relevant or uncertain step it is about to execute → decision-kit's `consulting-decision-model`, when decision-kit is installed."
- codex-peer-review is ruled out by "An existing written plan or document file to check → `codex-verify`."

Caveat: codex-verify sends the whole docs/deploy-plan.md, and its PASS/FAIL verdict covers the whole document, not only the rollback step.

## 2. "cross-model review this diff before I open the PR" → `cross-model-review`

The request names a diff, asks for a cross-model review and sets the review before the PR. It does not ask for a Codex-only opinion.

Deciding sentences:
- cross-model-review When to Use: "Before a PR is created (draft or ready-to-merge), or before a draft PR is flipped to ready — when an independent, cross-vendor pass on the current diff is wanted before it becomes visible on GitHub. Also for an explicit \"adversarial review,\" \"cross-model review,\" or \"second-opinion review\" request on the working diff."
- cross-model-review When NOT to Use (tie-break): "a diff, branch or PR named with no Codex-only ask comes here; asking Codex about a design, analysis or document goes to the codex-kit skill, even with code changes attached."
- codex-verify Testing & Validation: "\"cross-model review this diff before I open the PR\" → git-kit's `cross-model-review`". Its When NOT to Use adds: "This skill verifies a document, not a diff."
- codex-peer-review When NOT to Use: "A two-vendor review of the working diff as a gate before a PR is created or a draft is flipped to ready → git-kit's `cross-model-review`."
