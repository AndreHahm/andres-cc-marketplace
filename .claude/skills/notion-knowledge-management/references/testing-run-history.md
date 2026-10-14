# Testing Run History

Dated `skill-tester` iterations for `notion-knowledge-management`, newest first. SKILL.md's "Last dated
run record" line points at the latest; the older entries live here.

- **iteration-6 (2026-10-14), `evals/notion-knowledge-management/workspace/iteration-6/`** — Quick
  Workflow, simulate-only, `with_skill` agents only. Re-ran evals 8-11 against the audit-edited skill
  and added evals 12-15 (null `notion.repo` with an adopted database missing the option, an unmatched
  `repo` option, a 2,600-character property, the `status-and-learning` boundary). 46/46 assertions,
  including a new per-eval assertion that every tool the skill itself plans to call is in its
  `allowed-tools`. Eval 11's fourth assertion changed from "confirms the block count" to the paragraph-count
  and closing-sentence check, after a live test-environment write on 2026-10-13 showed the read-back
  returns Markdown with no block structure. Eval 15's "does not build a preview itself" is a weak pass:
  the agent showed an illustrative, unfilled sketch with a title.

- **iteration-5 (2026-10-13), `evals/notion-knowledge-management/workspace/iteration-5/`** — Quick
  Workflow, simulate-only, `with_skill` agents only (no baseline, no `benchmark.json`). Evals 8-11 cover
  the org-level migration: required `repo` from `notion.repo`, stop when it is unset, two-scope
  Bootstrap with a move candidate, and long text as page-content blocks. 18/18 assertions. Its eval 10
  planned `notion-move-pages`, which the skill did not then grant; the grading did not catch that, and
  the grant was added afterwards.
- **iteration-4 (2026-09-20, `workspace/iteration-4/eval-7/`)** — eval 7: every declared positive
  trigger phrase maps to vocabulary in the frontmatter description (a description-consistency check by
  the orchestrating agent, not a full task simulation).
- **iteration-3 (2026-09-12)** — closed the 2 uncovered trigger phrases ("propose a goal for Q3", "log
  this as a research note").
- **iteration-2 (2026-09-11)** — Phase 7 Deep Test re-run verifying the Write and
  `Bash(wmgt_bridge_caller.py:*)` grants and the restructured classification-help approval gate.
- **iteration-1 (2026-08-30)** — first run.
