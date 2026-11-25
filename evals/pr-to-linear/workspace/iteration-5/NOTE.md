# iteration-5 (2026-11-25): every triage run asks first

Plan-only, one agent per eval and arm (9 agents), model read from the transcripts (in each grading.json). Each agent
was told to read only its one skill text, under a neutral file name. Graded by the author, who knew the arms.

- `with_skill` is the text that asks before every triage run, `baseline` the text of eba24a03. Both lack Testing &
  Validation. Eval 5 ran on the new text only.
- Result: `with_skill` 5 of 5, `baseline` 2 of 4. The baseline ran triage without asking in evals 7 and 9; evals 10
  and 11 did not separate the arms. One run per arm, so this is no effect size.
- The assertion texts of evals 9 to 11 were written after the answers were read.
- Eval 7's expected output is reversed from iteration-4: an explicit fix request now gets the question too. Evals 1
  to 4, 6 and 8 were not repeated; eval 1's expected output was changed to include the question.
