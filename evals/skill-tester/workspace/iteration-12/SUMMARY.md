# Iteration 12: trailing-newline instruction (non-discriminating)

Target: the sentences telling an agent to end `eval_metadata.json` / `grading.json` with a trailing newline, in `skill-tester/SKILL.md` (Steps 2.3 and 4.2), `skill-development`'s `agents/grader.md` (Step 8) and `references/eval-workflow.md`.

**Arms.** `with_skill` read the committed text. `baseline` read the same documents as they were before the sentences were added (not a no-skill baseline), so the only difference is the sentence. Prompts never mention newlines. Pass check is mechanical: file exists, parses as JSON, last byte is `0x0A`.

**Runs.** One run on the default (inherited) model, then three runs on haiku, each covering all four scenarios and both arms (32 agents in all, one per scenario, arm and run).

| Eval | Scenario | with_skill: files ending in newline | baseline: files ending in newline |
|---|---|---|---|
| 5 | step-2-3-eval-metadata-newline | 8/8 | 8/8 |
| 6 | step-4-2-grading-newline | 8/8 | 8/8 |
| 7 | grader-step-8-grading-newline | 4/4 | 4/4 |
| 8 | eval-workflow-both-files-newline | 12/12 | 12/12 |
| | **Total** | **32/32** | **32/32** |

## Reading

Both arms wrote a final newline every time, so this run cannot show that the sentences have any effect. It is a null result, not evidence for or against them.

The failure is rare in practice: before the 35-file data fix, 27 of 1,747 tracked `eval_metadata.json` and `grading.json` files (about 1.5%) lacked the newline, all from the most recent `triaging-dependabot-prs` and `plugin-rulebook` iterations. At that rate about 0.5 failures would be expected among the baseline's 32 files, so the sample is far too small to detect an effect. The writer that produced the missing newlines was not identified.

## Reproducing

- **The two document versions per scenario.** `with_skill` is the file at its current path in
  `HEAD`; `baseline` is the same file as it was before the commit titled "tell eval writers to
  end JSON files with a newline" (`git show <that commit>^:<path>`). The paths are
  `plugins/plugin-devkit/skills/skill-tester/SKILL.md` (evals 5 and 6),
  `plugins/plugin-devkit/skills/skill-development/agents/grader.md` (eval 7) and
  `plugins/plugin-devkit/skills/skill-development/references/eval-workflow.md` (eval 8).
- **The task.** The `prompt` of each eval in `evals.json`, with `<OUT>` replaced by an empty
  scratch directory the agent writes to and the document copied to a neutrally named file.
  For eval 7 (the grader), `<OUT>` is the directory holding a short `transcript.md` and an
  `outputs/` subdirectory with a one-line `answer.md`; the grading file is saved in `<OUT>` itself.
- **The pass check.** `python check_trailing_newline.py <output-dir> <expected-file-count>`
  (counts: 2, 2, 1 and 3 for evals 5 to 8). This checker is the only script persisted here.

## Not recorded

- Raw agent outputs are not persisted: they are trivial fixture JSON, and files in `outputs/` that lack a newline would be rewritten by the repository's end-of-file hook, destroying the very property under test.
- No `benchmark.json` or `timing.json`: the aggregation script expects one run per configuration, and this iteration has four runs per arm.
- Agents were not checked for which tool wrote each file.
