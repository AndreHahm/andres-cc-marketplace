# Routing judgments (set-b)

## 1. "verify step 3 of plan.md"

- **Chosen skill:** codex-verify
- **Deciding quote:** codex-verify description: "Verify a plan or document using Codex as independent reviewer with PASS/FAIL verdict. Use when asked \"codex verify\", \"verify this plan\", \"review this doc for issues\"", and "codex-verify performs one PASS/FAIL check of an already-existing document". The target is a named, existing file (plan.md). consulting-decision-model's When NOT to Use also routes "a written plan or document (`codex-verify`)" away from itself.
- **Second plausible skill:** consulting-decision-model. Its When NOT to Use says "This skill covers one action or choice Claude is about to execute, including a single irreversible step from a plan." That fits only if step 3 is an irreversible action Claude is about to run. The request says "verify" a section of a document and does not mention executing it, so codex-verify still wins. The two skills' boundary is unclear when one plan step is the object.

## 2. "verify this plan with codex"

- **Chosen skill:** codex-verify
- **Deciding quote:** codex-verify: "Use when asked \"codex verify\", \"verify this plan\"". consulting-decision-model's negative trigger list maps this exact phrase: "\"verify this plan with codex\" → `codex-verify`".
- **Second plausible skill:** codex-peer-review, only weakly. Its description says "Validate Claude's own analysis, design, or recommendation against Codex", which matches if "this plan" is a plan Claude stated in chat rather than a file. Its own line "For verifying an existing written plan/document file, use codex-verify instead" sends the file case back to codex-verify.

## 3. "before you force-push, check whether that's safe"

- **Chosen skill:** consulting-decision-model
- **Deciding quote:** "Use before an irreversible action Claude chose (deleting data, force-pushing, a migration, publishing) ... or for \"ask the decision model\", \"check this decision before you do it\" or \"is this action safe to proceed\"". It also lists "Claude choosing a force-push or a permission change on its own" as an activation case. The exclusion "Not when the user ordered that exact action on their own judgment" does not apply: the user did not order the force-push. They asked for a safety check before Claude does it.
- **Second plausible skill:** none. cross-model-review, codex-peer-review and codex-verify cover a diff, a design or recommendation, and a document. None of them covers judging a single git action before it runs.
