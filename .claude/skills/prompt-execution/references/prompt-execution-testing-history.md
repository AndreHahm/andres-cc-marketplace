# prompt-execution Testing History

Run history of the prompt-execution skill: what was run, when and with what result. Nothing here is
needed to use the skill. Paths starting with `workspace/` are below `evals/prompt-execution/`,
and so is a bare `iteration-N/`.

## Hand-followed and live runs

On 2026-10-04 a subagent followed the skill's SKILL.md by hand against a valid and a tampered throwaway catalog: a
metacharacter slug was refused with no command run, a valid prompt was previewed and the flow stopped at
the approval question without running anything, and the tampered catalog was reported unavailable. That
run was not persisted and the approval question could not be asked. A later live interactive run on
2026-10-14 (plugin loaded with `--plugin-dir`) answered Cancel, which ran nothing, and then approved one
prompt, which was rechecked and ran once.

## Evals

`evals/prompt-execution/` holds with-skill versus baseline scenarios run by dry-run agents that
follow the skill's SKILL.md by hand against throwaway projects (the approval question scripted). Its `evals.json`
records which quality gates the scenarios cover. Eval 7 (2026-11-12, `workspace/iteration-2/eval-7/`, plan-only)
checks that a free-text approval naming new slugs runs nothing and takes no slug from the answer: 4 of 4 with the
skill and 4 of 4 for the pre-fix text, so it shows no measured difference; the step 5 wording now states the rule
the baseline had to infer from step 1. Eval 8 (same date and folder) checks the hidden-character preview and
approval: 5 of 5 with the skill against 4 of 5 for the `main` text, whose approval question named no counts.
On 2026-11-15 all eight scenarios were re-run with and without the skill against real fixture projects
(`workspace/iteration-3/`, eval 8 now on a fixture with real hidden characters), replacing the 2026-10-04
baselines in `iteration-1/`: a mean per-scenario pass rate of 100% with the skill against 61.3% without. These dry runs are separate from the live `--plugin-dir`
run recorded above, and no eval has been run from a marketplace install. On 2026-11-25 eval 3 (rewritten: a
changed prompt blocks only itself, with-skill only) passed 3 of 4 (`iteration-5/`) and, after step 3's wording was
tightened, 4 of 4 (`iteration-6/`).
