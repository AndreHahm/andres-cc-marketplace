# Routing: second-opinion review of the working diff before opening a PR

**Route: do not use `codex-peer-review`. Use `/codex-kit:cdx-review`, since git-kit is not installed.**

## Why this skill does not take the request

`codex-peer-review` validates Claude's own position (an analysis, design, or recommendation) against Codex. The request is a review of a code diff, which is a different job:

- The "When NOT to Use" section excludes "a two-vendor review of the working diff as a gate before a PR is created or a draft is flipped to ready." That gate belongs to git-kit's `cross-model-review`.
- The tie-break rule says a diff, branch, or PR named with no Codex-only ask goes to `cross-model-review`. This request names the working diff and the PR, and it does not ask for a Codex-only check of a position. So it does not stay here.
- The Testing section lists this exact phrasing ("second-opinion review of this diff before I open the PR") as a case that should NOT activate this skill.

## Fallback, since git-kit is not installed

The SKILL.md text says that without git-kit, `/codex-kit:cdx-review` reviews the diff. That is the closest installed option.

Tradeoff to tell the user: `cross-model-review` is two-vendor (Claude reviews natively, Codex reviews independently, then they cross-examine each other). `/codex-kit:cdx-review` is Codex only, so the Claude-side review and the cross-examination step are not available in this session.

## Not done

- No Codex call, no subagent dispatch, and no command was run. This answer comes from the skill text alone.
- Nothing was edited. The only file written is this response.
