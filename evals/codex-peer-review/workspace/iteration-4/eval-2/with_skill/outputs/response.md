# Routing

## Request 1: "have codex sanity-check the caching approach you just proposed"

**Skill: codex-peer-review**

Why: the caching approach is a design position Claude has already formed and has not yet presented or written to a file. The user wants Codex to check that position. The skill's When to Use section covers this case directly ("Claude has formed an analysis, design or recommendation that is not yet presented or written to a file, and the user wants Codex to check it first").

Rejected alternatives:
- `codex-verify`: only for an existing written plan or document file. The caching approach has no file yet.
- `cross-model-review`: only for a diff, branch or PR. No code changes are named.
- `consulting-decision-model`: only for one critical, security-relevant or uncertain action Claude is about to execute. Here the user is asking for a design check, not a go/no-go on an action.
- `codex-research`: only when there is no Claude position to validate. Claude already has one.

## Request 2: "get a second-opinion review of my working diff before I open the PR"

**Skill: cross-model-review**

Why: this is a second-opinion review of the working diff as a gate before a PR is created. The codex-peer-review skill's own Testing & Validation section names this exact phrasing ("second-opinion review of this diff before I open the PR") as a case that goes to git-kit's `cross-model-review`, not to codex-peer-review. The "When NOT to Use" tie-break also applies: a diff named with no Codex-only ask goes to `cross-model-review`.

Rejected alternatives:
- `codex-peer-review`: Codex-only, and meant for validating Claude's position rather than a pre-PR gate on the diff.
- `codex-verify`: for an existing written plan or document, not a diff.
- `consulting-decision-model`: not a single execution-time action.

Note: `cross-model-review` is a git-kit skill. It is listed in this session's available skills, so it is used directly.

## Summary

| Request | Skill |
|---|---|
| Codex sanity-check of the caching approach just proposed | codex-peer-review |
| Second-opinion review of the working diff before opening the PR | cross-model-review |
