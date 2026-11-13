# Routing judgments (set-b)

## 1. "get a codex second opinion on this design"

- **Chosen skill:** `codex-peer-review`
- **Deciding quote:** codex-peer-review description: "Validate Claude's own analysis, design, or recommendation against Codex before presenting it to the user. Use manually/on-request only — e.g. \"get a second opinion from codex before we commit to this\", \"codex peer review this design\"." Reinforced by consulting-decision-model's negative list: "\"get a second opinion from codex on this design\" → `codex-peer-review`".
- **Second plausible skill:** `cross-model-review`, weakly — its description says "Use for an adversarial review, a cross-model or second-opinion review". It loses because its object is "the current diff" before a PR, not a design.

## 2. "review my diff before I open the PR"

- **Chosen skill:** `cross-model-review`
- **Deciding quote:** cross-model-review description: "Reviews the current diff adversarially across two model vendors before a PR is created (draft or ready)" and "Use for ... a pre-PR gate, or high-confidence findings before opening or readying a PR." Reinforced by consulting-decision-model's negative list: "\"review my diff before the PR\" → `cross-model-review`".
- **Second plausible skill:** none. codex-verify's "review this doc for issues" shares the verb but targets "an already-existing document", not a diff.

## 3. "check this decision before you run that migration"

- **Chosen skill:** `consulting-decision-model`
- **Deciding quote:** consulting-decision-model description: "Use before an irreversible action Claude chose (deleting data, force-pushing, a migration, publishing) ... or for \"ask the decision model\", \"check this decision before you do it\"". When to Use table: "`critical` | An irreversible or hard-to-reverse action Claude chose: deleting data, force-pushing, migrating, merging, publishing".
- **Second plausible skill:** `codex-peer-review`, weakly — "Validate Claude's own analysis, design, or recommendation against Codex before presenting it to the user." It loses because the request is about an action Claude is about to execute, not a recommendation to present, and it names no Codex; consulting-decision-model's "this skill judges one action or choice Claude is about to execute" decides it. Caveat: if the user had themselves ordered the migration, consulting-decision-model's exclusion "Not when the user ordered that exact action on their own judgment" would apply, but "check this decision" asks for the check explicitly.
