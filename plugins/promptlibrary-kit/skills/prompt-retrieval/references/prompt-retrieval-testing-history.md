# prompt-retrieval Testing History

Run history of the prompt-retrieval skill: what was run, when and with what result. Nothing here is
needed to use the skill. Paths starting with `workspace/` are below `evals/prompt-retrieval/`,
and so is a bare `iteration-N/`.

## Hand-followed and live runs

On 2026-10-04 a subagent followed the skill's SKILL.md by hand
against two throwaway fixtures (a valid catalog and a tampered one) and the quality gates SKILL.md listed then passed,
except that the `root_source` wording in the second gate was corrected afterward and that corrected
wording was not part of that run. A headless live run on 2026-10-14 (plugin loaded with `--plugin-dir`)
then ran this skill; see the README's Known limitations.

## Evals

`evals/prompt-retrieval/` holds with-skill versus baseline scenarios run by dry-run agents that
follow the skill's SKILL.md by hand against throwaway projects. Its `evals.json` records which quality gates the
scenarios cover. On 2026-11-15 all five scenarios (adding 4 for hidden characters and 5 for a malformed slug)
were run with and without the skill against real fixture projects (`workspace/iteration-2/`), replacing the
2026-10-04 baselines in `iteration-1/`: a mean per-scenario pass rate of 100% with the skill against 65.7%
without (`benchmark.json` shows 65.6% because its aggregator rounds each scenario's rate first). These dry runs
are separate from the live `--plugin-dir` run above, and no eval has been run from a marketplace install.
On 2026-11-24 scenario 6 (search, with-skill only, `workspace/iteration-4/`) passed 4 of 4 checks after step 2
was reworded. Later that day scenarios 6 and 7 ran after the status filter was reworded (`workspace/iteration-5/`,
3 of 4 each) and again after steps 2 and 4 were reworded for the two failed checks (`workspace/iteration-6/`, 4 of 4 each);
with-skill only, no baseline, and neither run exercised the topic retry. Scenario 8 (drafts only, whole words, `workspace/iteration-7/`) passed 2 of 2
after the review fixes; scenarios 6 and 7 were not run again.
On 2026-11-25 scenario 3 (rewritten: a changed prompt is listed as changed, with-skill only,
`workspace/iteration-8/`) passed 4 of 4.
