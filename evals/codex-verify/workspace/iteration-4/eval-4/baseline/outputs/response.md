# Routing: "cross-model review this diff before I open the PR"

**Not `codex-verify`.** This request should not go to codex-verify, and the skill's own text gives the reason.

- codex-verify performs one PASS/FAIL check of an existing plan or document file. Its scope line says: "This skill verifies a document, not a diff." (When NOT to Use, last bullet.)
- The skill's own description sends a two-vendor review of a working diff before a PR to git-kit's `cross-model-review`. The same routing appears in the When NOT to Use list and in Testing & Validation (the scenario "cross-model review this diff before I open the PR" → git-kit's `cross-model-review`).

**Consequence in this session.** git-kit is not installed, so the named destination is unavailable. The skill text names no other fallback for a two-vendor pre-PR diff review. It does name `/codex-kit:cdx-review` for code review in general (Purpose line and When NOT to Use), but it describes that as a code-review command, not as the two-vendor pre-PR review, so I would not present it as a substitute without saying so. codex-verify should not be used as a workaround: it accepts a file path, not a diff, and running it on a diff would be outside its contract.

**Recommended action.** Tell the user that the cross-model diff review belongs to git-kit's `cross-model-review`, which is not installed here. Options to offer, not to decide for them: install git-kit and run `cross-model-review`, or, if they accept a single-vendor review, run `/codex-kit:cdx-review` and state that it is not the two-vendor review the skill describes.
