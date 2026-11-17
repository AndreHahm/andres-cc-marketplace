# Routing per codex-peer-review's own text

## (a) Review the already-open PR #123 and leave review comments → **neither**

- **Not codex-peer-review.** This skill only validates *Claude's own* analysis, design or recommendation
  that has not yet been presented or written to a file (When to Use). Reviewing someone's open PR and
  posting comments is not a Claude position to check with Codex. The skill also fires only on an explicit
  request such as "codex peer review this design".
- **Not cross-model-review.** The skill sends to git-kit's `cross-model-review` only "a two-vendor review
  of the working diff as a gate before a PR is created or a draft is flipped to ready". PR #123 is already
  open, so it is not a pre-PR gate, and nothing in that route covers leaving comments on a PR.
- **So another skill handles it.** codex-peer-review's text does not name which one: none of its "When NOT
  to Use" routes covers acting as a reviewer on an open PR. Its own text only rules out the two
  candidates; it does not name the right one.

## (b) Get a second-opinion review of my working diff before I open the PR → **cross-model-review**

- The skill's Testing & Validation section lists this exact phrasing as a non-activation case:
  "second-opinion review of this diff before I open the PR" → git-kit's `cross-model-review`.
- The "When NOT to Use" tie-break agrees: "a working diff or local branch with no Codex-only ask goes to
  `cross-model-review`". The request names a working diff, a pre-PR moment and no Codex-specific design,
  analysis or recommendation question, so it is that pre-PR gate, not a check of Claude's own position.
- **Condition:** this route holds when git-kit is installed. Without git-kit, the skill says the user can
  run `/codex-kit:cdx-review` themselves (Codex only); Claude cannot invoke it, and codex-peer-review
  still does not take the request on.
