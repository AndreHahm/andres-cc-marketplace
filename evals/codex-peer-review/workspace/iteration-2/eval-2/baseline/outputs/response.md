# Routing answer (baseline skill text)

## 1. "have codex sanity-check the caching approach you just proposed"

**Skill: codex-peer-review**

Deciding text:
- codex-peer-review description: "Validate Claude's own analysis, design, or recommendation against Codex before presenting it to the user."
- codex-peer-review When to Use: "Claude has formed an analysis, design or recommendation that is not yet presented or written to a file, and the user wants Codex to check it first." Also: "On explicit request only: ... \"codex peer review this design\"."
- Excluded alternatives: codex-verify is for "an existing written plan or document file" ("For validating Claude's own not-yet-written analysis or design (no document to point at), use codex-peer-review instead."). consulting-decision-model is for "one critical, security-relevant or uncertain action or choice Claude is about to execute", and a caching design is not one action about to run. cross-model-review reviews a diff, and there is none here.
- Ambiguity: the approach was "just proposed", so it has arguably already been presented, which strains "before presenting it". No other skill covers a design held only in the conversation, so codex-peer-review still wins. Codex is named explicitly, so the Model check does not fire.

## 2. "get a second-opinion review of my working diff before I open the PR"

**Skill: cross-model-review**

Deciding text:
- cross-model-review description: "Reviews the current diff adversarially across two model vendors before a PR is created (draft or ready)" and "Use for an adversarial review, a cross-model or second-opinion review, a pre-PR gate, or high-confidence findings before opening or readying a PR."
- cross-model-review When to Use: "Before a PR is created (draft or ready-to-merge) ... Also for an explicit \"adversarial review,\" \"cross-model review,\" or \"second-opinion review\" request on the working diff."
- Excluded alternatives: codex-peer-review validates "Claude's own analysis, design, or recommendation", not the user's diff. Its "second opinion" trigger phrases and its `review --base` command for diffs create some overlap, but the request names no Codex and no Claude position. codex-verify is for a plan or document file. consulting-decision-model is for a single action, and cross-model-review says: "This skill reviews a diff, never one decision."
