# Routing: "cross-model review this diff before I open the PR"

**Answer:** this does not go to `codex-verify`. With git-kit not installed, it goes to `/codex-kit:cdx-review`.

## Basis in codex-verify's own text

- **When NOT to Use** (line 61-62): "Code review → `/codex-kit:cdx-review`, or git-kit's `cross-model-review` (when git-kit is installed) for a two-vendor review of the working diff before a PR. This skill verifies a document, not a diff."
- **Testing & Validation, "Verify it does NOT activate on"** (line 418): "cross-model review this diff before I open the PR" → git-kit's `cross-model-review`, when git-kit is installed (without it, `/codex-kit:cdx-review`).
- **Description** (line 16-18): a pre-PR two-vendor diff review goes to git-kit's `cross-model-review`, if installed.

## Why codex-verify does not fit

codex-verify takes one existing document and returns one PASS/FAIL verdict. It is not built for a diff. Its Phase 1 assembles a blind payload from a document path, so a diff is not something it can take.

## Recommended route

Since git-kit is not installed in this session, use `/codex-kit:cdx-review` for the Codex side of the review. Note that the two-vendor cross-examination that `cross-model-review` provides is not available here.
