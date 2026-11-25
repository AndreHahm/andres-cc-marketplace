# iteration-4 (2026-11-25): Quick Start added (issue #461 step 3)

Quick Workflow, with_skill only, plan-only, one agent per eval, 11 of 13 assertions. Graded by the author.

- Model: claude-haiku-5-5, read from the agents' transcripts. The session model changed during the run, so
  the nine skills' results are not comparable with each other: 64 of 70 on Haiku 5.5 (20 evals), 28 of 28 on
  Opus 5.5 (8 evals).
- The agent got the stored prompt and the skill text without its Testing & Validation section, and could read
  FOUNDATION_CONTRACTS.md (repository-gates also repository configuration). No connector, git or gh call.
- No baseline arm, so a missed assertion here does not show its cause.
- The skill text tested used ENG-123 as the Quick Start's example ID where one appears. It was replaced by
  `<issue-id>` afterwards, and this iteration was not repeated with the new text.
- The trigger-phrase eval was not run: the frontmatter is unchanged.
