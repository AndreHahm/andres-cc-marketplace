# Routing judgments (set-a)

## 1. "verify step 3 of plan.md"

- **Chosen skill:** codex-verify
- **Deciding quote:**
  - consulting-decision-model, "Verify it does NOT activate on": `"verify step 3 of plan.md" (the user asks for the check) → codex-verify`
  - consulting-decision-model, When NOT to Use: "When the user asks for a plan or document to be verified, that stays with `codex-verify`, even if Claude will later execute a step from it."
  - codex-verify description: "Verify a plan or document using Codex as independent reviewer with PASS/FAIL verdict. Use when asked \"codex verify\", \"verify this plan\" ..."
- **Second plausible skill:** consulting-decision-model. It covers "one action or choice Claude is about to execute, including a single irreversible step from a plan", and codex-verify's description says "For one critical, security-relevant or uncertain step of a plan that Claude is about to execute, use consulting-decision-model instead". The request names a single step, so that line makes it plausible. It loses because the user asks for the verification (no action is about to run), and both files' explicit tie-breakers route this case to codex-verify.

## 2. "verify this plan with codex"

- **Chosen skill:** codex-verify
- **Deciding quote:**
  - codex-verify description: "Use when asked \"codex verify\", \"verify this plan\", \"review this doc for issues\""
  - consulting-decision-model, "Verify it does NOT activate on": `"verify this plan with codex" → codex-verify`
- **Second plausible skill:** codex-peer-review, weakly. It is the other skill that validates something "against Codex" ("get a second opinion from codex before we commit to this"). It is ruled out by its own line: "For verifying an existing written plan/document file, use codex-verify instead." The request says "this plan", which points to an existing plan.

## 3. "before you force-push, check whether that's safe"

- **Chosen skill:** consulting-decision-model
- **Deciding quote:**
  - consulting-decision-model description: "Use before an irreversible action Claude chose (deleting data, force-pushing, a migration, publishing) ... or for \"ask the decision model\", \"check this decision before you do it\" or \"is this action safe to proceed\"."
  - When to Use table: "`critical` | An irreversible or hard-to-reverse action Claude chose: deleting data, force-pushing, ..."
  - Activation list: "Claude choosing a force-push or a permission change on its own"
- **Second plausible skill:** none. cross-model-review reviews a diff and sends this case away: "Checking one action or choice Claude is about to execute ... that's decision-kit's `consulting-decision-model`". Neither codex-peer-review nor codex-verify matches a single pending action. One caveat: the exclusion "Not when the user ordered that exact action on their own judgment" (the negative example is "force-push this branch") does not apply here. The phrasing "before you force-push" points to a force-push Claude is about to run, and the user is asking for the check rather than giving an order.
