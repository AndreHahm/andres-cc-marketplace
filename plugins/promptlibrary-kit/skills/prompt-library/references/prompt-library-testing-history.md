# prompt-library Testing History

Run history of the prompt-library skill: what was run, when and with what result. Nothing here is
needed to use the skill. Paths starting with `workspace/` are below `evals/prompt-library/`,
and so is a bare `iteration-N/`.

## Hand-followed and live runs

The latest live run, 2026-10-14 (plugin loaded with
`--plugin-dir`), ran add, near-duplicate, revise, finalize and deactivate, each status change behind its
own approval; the step 5 triage skip it found was fixed in PR #566. An earlier hand-followed run of steps
1 to 6 (2026-10-04, not persisted) confirmed a fake key is reported unechoed and refused by `draft`.

## Evals

`evals/prompt-library/` holds with-skill versus baseline scenarios run by dry-run agents that
follow the skill's SKILL.md by hand against throwaway projects (approval questions scripted, the reviewer step done
inline). Its `evals.json` records which quality gates the scenarios cover. Scenario 11 (draft resume,
2026-11-12, with-skill only, in `workspace/iteration-2/`) first passed 3 of 4 checks: no read
subcommand returned the record path. After `path` was added to `show` (covered by a unit test), a re-run
the same day passed 4 of 4. Scenario 12 (a session draft with only its quality verification resumes at
step 8, read from `missing_verification`) passed 5 of 5 the same day. Scenario 13 (recovery advice for a
pathspec-shaped `errors` path) passed 5 of 5 against 3 of 5 for the earlier `git restore <path>` text.
On 2026-11-15 every scenario was re-run with and without the skill against real fixture projects
(`workspace/iteration-3/`, scenarios 1 to 15, adding 14 for an already active record and 15 for a
malformed slug), replacing the 2026-10-04 baselines in `iteration-1/`: a mean per-scenario pass rate of 95.6%
with the skill against 53.4% without. Scenario 5 failed there (1 of 3, 3 of 3 on 2026-10-04): the step 5 "existing script" rule,
added 2026-10-14, made text carrying its own parser a prompt. After the rule was narrowed, `iteration-4/` re-ran
scenario 5 and a new scenario 16 (text that only names a script stays a prompt): a mean pass rate of 100% with
the skill against 25% without. These dry runs are separate from the live
`--plugin-dir` run recorded above, and no eval has been run from a marketplace install.
On 2026-11-24 scenario 23 (discard, with-skill only, `workspace/iteration-9/`) passed 5 of 5 checks, and
scenario 24 (Keep, and a suspicious orphan name, `workspace/iteration-10/`) passed 3 of 3.
On 2026-11-25, with-skill only: scenario 6 (rewritten: a changed prompt blocks only itself) passed 2 of 4
(`iteration-13/`) and, after step 2 was corrected, 4 of 4 (`iteration-14/`); scenario 25 (retire) passed 3 of 3; scenarios 26 and 27 (`iteration-15/`) passed 4 of 4 each.
