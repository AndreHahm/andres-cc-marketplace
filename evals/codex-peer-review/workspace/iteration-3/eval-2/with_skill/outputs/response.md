# Routing answer

## 1. "have codex sanity-check the caching approach you just proposed" → `codex-peer-review`

The caching approach is Claude's own design. It has not been written to a file, it is not a working diff, and it is not one action Claude is about to execute. The user asks Codex to check it.

These sentences decide it:
- codex-peer-review description: "Validate Claude's own analysis, design, or recommendation against Codex before presenting it to the user."
- codex-peer-review When to Use: "Claude has formed an analysis, design or recommendation that is not yet presented or written to a file, and the user wants Codex to check it first."
- codex-peer-review tie-break: "asking Codex about a design, analysis or recommendation stays here, even with code changes attached".
- cross-model-review When NOT to Use (the same split from its side): "A Codex-only second opinion: on Claude's own design, analysis or recommendation → codex-kit's `codex-peer-review`".
- Why `codex-verify` does not fit: "Claude's own not-yet-written analysis or design, with no document to point at → `codex-peer-review`."
- Why `consulting-decision-model` does not fit: it covers "One critical, security-relevant or uncertain action or choice Claude is about to execute". This request is a design check the user asked for, not an execution-time check of one action.

## 2. "get a second-opinion review of my working diff before I open the PR" → `cross-model-review`

The request names the working diff and the time before a PR is opened. It does not ask for a Codex-only check.

These sentences decide it:
- cross-model-review description: "Use for an adversarial review, a cross-model or second-opinion review of the working diff, a pre-PR gate, or high-confidence findings before opening or readying a PR."
- cross-model-review When to Use: "Before a PR is created (draft or ready-to-merge) ... Also for an explicit "adversarial review," "cross-model review," or "second-opinion review" request on the working diff."
- cross-model-review tie-break: "a diff, branch or PR named with no Codex-only ask comes here".
- codex-peer-review When NOT to Use (the same split from its side): "A two-vendor review of the working diff as a gate before a PR is created or a draft is flipped to ready → git-kit's `cross-model-review`." Its Testing section also lists "second-opinion review of this diff before I open the PR" → git-kit's `cross-model-review`.
- codex-verify: "A two-vendor review of a working diff before a PR goes to git-kit's cross-model-review." It also says: "This skill verifies a document, not a diff."
