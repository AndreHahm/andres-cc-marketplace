# iteration-4 (2026-11-25): routing between the lifecycle and its stage skills

Two arms, plan-only, one agent per eval and arm (20 agents), claude-opus-5-5 read from the transcripts. Every
agent read only its one skill text. Graded by the author, who knew the arms.

- `with_skill` is the text in this pull request, `baseline` the same text without the routing bullet (for the
  lifecycle skill, with its earlier single-stage bullet). Both arms lack the Testing & Validation section.
- The agents saw neutral file names. The skill list in each prompt names `linear-github-lifecycle`.
- Result: 10 of 10 in both arms, so this shows no effect of the routing text. No dispatched skill routed back.
- In three of the four hand-over evals the baseline agent said it inferred the target from the skill's name; in the
  fourth it used the skill's mention as an orchestrator. All four `with_skill` agents cited the new text.
- Selection by description is not tested: the frontmatter is unchanged. One run per arm, no real dispatch.
- One intro sentence of the lifecycle skill (which phases are delegated) was reworded after the run and not re-run.
