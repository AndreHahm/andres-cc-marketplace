# Routing answer

## 1. "have codex sanity-check the caching approach you just proposed"

**Skill: `codex-peer-review`**

Deciding text (codex-peer-review/SKILL.md):
- description: "Validate Claude's own analysis, design, or recommendation against Codex before presenting it to the user."
- When to Use: "Claude has formed an analysis, design or recommendation that is not yet presented or written to a file, and the user wants Codex to check it first."
- when_to_use example: "get a second opinion from codex before we commit to this", "codex peer review this design".

Why not the others:
- `codex-verify`: "For validating Claude's own not-yet-written analysis or design (no document to point at), use codex-peer-review instead." The caching approach is not a document file.
- `cross-model-review`: "A second opinion with no diff: Claude's own design, analysis or recommendation → codex-kit's `codex-peer-review` ... This skill reviews a diff."
- `consulting-decision-model`: reserved for "one critical, security-relevant or uncertain action or choice Claude is about to execute"; this is a design to validate, not an action about to run.

Caveat: "you just proposed" implies the approach was already shown in chat, while the When to Use line says "not yet presented". It is still not written to a file and Codex is named explicitly, so `codex-peer-review` remains the only fit. Because Codex is named, the Model check's ambiguous-model ask does not fire.

## 2. "get a second-opinion review of my working diff before I open the PR"

**Skill: `cross-model-review`**

Deciding text (cross-model-review/SKILL.md):
- When to Use: "Before a PR is created (draft or ready-to-merge) ... Also for an explicit \"adversarial review,\" \"cross-model review,\" or \"second-opinion review\" request on the working diff."
- description: "Use for an adversarial review, a cross-model or second-opinion review of the working diff, a pre-PR gate, or high-confidence findings before opening or readying a PR."
- Activation example: "cross-model review this diff" / "second-opinion review before I create the PR".

Confirmed by the exclusions in the other two skills:
- codex-peer-review When NOT to Use: "A second opinion on the working diff before a PR is created or a draft is flipped to ready → git-kit's `cross-model-review`. This skill validates a position, not a diff." Its Testing section also lists "second-opinion review of this diff before I open the PR" → `cross-model-review`.
- codex-verify When NOT to Use: "Code review → ... git-kit's `cross-model-review` for a two-vendor review of the working diff before a PR. This skill verifies a document, not a diff."
- `consulting-decision-model` is for one action, not a diff ("This skill reviews a diff, never one decision.").
