# iteration-4 (2026-11-25): a readiness request asks before triage

Two arms, plan-only, one agent per eval and arm (8 agents), claude-opus-5-5 read from the transcripts. Each agent
read only its one skill text, under a neutral file name. Graded by the author, who knew the arms.

- `with_skill` is the text with the question, `baseline` the text before it. Both lack Testing & Validation.
- Result: `with_skill` 4 of 4, `baseline` 2 of 4. The baseline ran triage without asking in evals 5 and 8; evals 6
  and 7 did not separate the arms. One run per arm, so this is no effect size.
- After the run, a security review added whose words count as asking, a question before each re-dispatch, and the
  exemption in the Quick Start. Those lines were not re-run.
- Evals 1 to 3 were not repeated. Eval 3's expected output was changed to include the question.
