# Routing

## Request 1: "have codex sanity-check the caching approach you just proposed"

**Skill: codex-peer-review**

Reasons:
- The target is Claude's own position (a caching approach it has just proposed), not a diff, branch, or PR. The skill's "Command selection" section says positions go to `task`, not `review --base`.
- The request names Codex explicitly, so the Model check's ambiguous-model ask does not fire. It is an explicit Codex selection.
- The proposal is not yet presented or written to a file, which matches "When to Use".

## Request 2: "get a second-opinion review of my working diff before I open the PR"

**Skill: cross-model-review** (git-kit)

Reasons:
- The target is a working diff before a PR is opened. codex-peer-review's own "When NOT to Use" section sends this to `cross-model-review`: "second-opinion review of this diff before I open the PR" is listed under its Testing & Validation "does NOT activate" cases.
- The request is a pre-PR gate with a diff as the object, and it is not a Codex-only question about a position. The tie-break in codex-peer-review ("a diff, branch or PR named with no Codex-only ask goes to `cross-model-review`") applies directly.
- codex-peer-review must not be used here, because it is a Codex-only check of Claude's own position and this request asks for a review of the diff.

## Not chosen

- codex-verify: for an existing written plan or document file. Neither request names one.
- consulting-decision-model: for one critical, security-relevant or uncertain action Claude is about to execute. Neither request is that.
- codex-plan-loop, codex-research, antigravity: not named or implied by either request.
