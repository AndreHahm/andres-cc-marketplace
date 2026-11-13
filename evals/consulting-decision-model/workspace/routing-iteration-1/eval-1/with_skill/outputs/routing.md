# Routing judgments (set-a)

## 1. "get a codex second opinion on this design"

- **Chosen skill:** codex-peer-review
- **Deciding quote:** codex-peer-review: `Use manually/on-request only — e.g. "get a second opinion from codex before we commit to this", "codex peer review this design".` and its activation list: `"get a second opinion from codex before we commit to this design"`. consulting-decision-model confirms it in its own exclusions: `"get a second opinion from codex on this design" → codex-peer-review`.
- **Second plausible skill:** cross-model-review, weakly. Its description says `Use for an adversarial review, a cross-model or second-opinion review`, and Codex is one of its two reviewers. It loses because it reviews `the current diff`, and the request names a design, not a diff.

## 2. "review my diff before I open the PR"

- **Chosen skill:** cross-model-review
- **Deciding quote:** cross-model-review: `Reviews the current diff adversarially across two model vendors before a PR is created` and `a pre-PR gate, or high-confidence findings before opening or readying a PR`. consulting-decision-model's exclusion list routes the same phrase here: `"review my diff before the PR" → cross-model-review`.
- **Second plausible skill:** none. codex-verify (`"review this doc for issues"`) needs a plan or document file, and codex-peer-review covers a design or analysis, not a diff.

## 3. "check this decision before you run that migration"

- **Chosen skill:** consulting-decision-model
- **Deciding quote:** consulting-decision-model: `Use before an irreversible action Claude chose (deleting data, force-pushing, a migration, publishing)` and `"check this decision before you do it"`. cross-model-review routes the same shape away from itself: `"check this decision before you run that command" (one action, no diff) → consulting-decision-model`.
- **Second plausible skill:** none for the request as worded. codex-verify would compete only if the migration came from a written plan the user asked to verify (`When the user asks for a plan or document to be verified, that stays with codex-verify`), and its own description sends a critical step Claude is about to run back to consulting-decision-model. One caveat: consulting-decision-model does not apply when `the user explicitly told Claude to do that exact action`. Here the user asks for a check, so it applies.
