# Routing: "get a second-opinion review of my working diff before I open the PR"

**Session:** only codex-kit is installed; git-kit is not.

## Answer

The request goes to **`/codex-kit:cdx-review`, which the user runs**. It is a Codex-only review.
It does not stay in `codex-peer-review`, and it cannot go to git-kit's `cross-model-review` in this session.

## Reasoning from codex-peer-review's own text

1. **This is the pre-PR working-diff case, not a peer review of a position.** Under "When NOT to Use",
   the skill excludes "A two-vendor review of the working diff as a gate before a PR is created or a
   draft is flipped to ready." Its tie-break says: "a working diff or local branch with no Codex-only ask
   goes to `cross-model-review`." The request is about the working diff before opening a PR. It contains
   no design, analysis or recommendation for Codex to validate, so `codex-peer-review` does not take it.
   The skill's "Verify it does NOT activate on" list names nearly the same phrase: "second-opinion review
   of this diff before I open the PR".

2. **The usual destination depends on git-kit, which is missing.** The redirect to `cross-model-review`
   is conditional: "when git-kit is installed". In this session it is not installed, so that route is
   unavailable.

3. **The skill names a fallback for this case.** The same bullet says: "without it, the user can run
   `/codex-kit:cdx-review`, Codex only; Claude cannot invoke it." The Testing section repeats the
   fallback for this exact request.

## What to tell the user

- Run `/codex-kit:cdx-review` yourself to get a Codex review of the working diff. Claude cannot launch
  this command for you.
- It is a Codex-only review, not the two-vendor cross-examination that `cross-model-review` provides.
  For that, install git-kit.
- If you actually want Codex to check a design, analysis or recommendation that Claude formed about
  these changes, ask for that explicitly, for example "codex peer review this approach". That request
  stays in `codex-peer-review`, even with code changes attached (it then uses `review --base`).
