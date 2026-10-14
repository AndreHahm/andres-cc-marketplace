# Testing Run History

Dated `skill-tester` iterations for `notion-knowledge-management`, newest first. SKILL.md's "Last dated
run record" line points at the latest; the older entries live here.

- **Live Bootstrap check (2026-10-14, Notion test environment, throwaway database)** — run by hand
  with the user's approval, not an eval. Verified: `notion-create-database` with a `repo` select;
  `notion-update-data-source` `ALTER COLUMN "repo" SET SELECT(...)` with the old and new option kept
  both, and the old option kept its ID; renaming only the data source left the parent page's child
  listing showing the old database title, and `notion-update-page` `update_properties` `title` then
  renamed the database title; `notion-move-pages` moved the database to another page with its options
  and data source name intact. A `notion-fetch` of the database reports the data source name, not the
  database title, so the parent listing is the check. Not tested: an `ALTER COLUMN` that omits an
  existing option (the tool's schema says it removes it), moving a database that holds rows, and any
  production database. The probe objects were trashed afterwards.
- **iteration-7 (2026-10-14), `evals/notion-knowledge-management/workspace/iteration-7/`** — Quick
  Workflow, simulate-only, `with_skill` agents only. Re-ran eval 12 (after `ALTER COLUMN` was documented
  as replacing the whole option list) and added evals 16-18, which with eval 15 cover all four "does NOT
  activate" phrases; `testing_validation_coverage` now counts 4 positive and 4 negative phrases, 8 of 8.
  First run 18/19: eval 18's agent routed to `status-and-learning` but also drafted a Report preview with
  placeholder figures, which fails the assertion that it drafts none; eval 16's agent previewed the Linear
  issue the other skill owns. SKILL.md then gained a routing rule (name the owning skill and stop, and
  do not draft or sketch the record it owns). Re-run of evals 15-18 against the changed skill: 17/17,
  each response only names the owning skill and plans a single `Skill(...)` hand-off. The hand-off
  `Skill(...)` calls are routing steps outside this skill's `allowed-tools`, and are noted, not counted
  as this skill's calls. The first-run outputs are kept in `with_skill/`, the re-runs in
  `with_skill_rerun/`.
- **iteration-6 (2026-10-14), `evals/notion-knowledge-management/workspace/iteration-6/`** — Quick
  Workflow, simulate-only, `with_skill` agents only. Re-ran evals 8-11 against the audit-edited skill
  and added evals 12-15 (null `notion.repo` with an adopted database missing the option, an unmatched
  `repo` option, a 2,600-character property, the `status-and-learning` boundary). 45/46 assertions after
  a regrade, including a new per-eval assertion that every tool the skill itself plans to call is in its
  `allowed-tools`. Eval 11's fourth assertion changed from "confirms the block count" to the paragraph-count
  and closing-sentence check, after a live test-environment write on 2026-10-13 showed the read-back
  returns Markdown with no block structure. Eval 15 was first graded 46/46 with a note calling its
  "does not build a preview itself" a weak pass (the agent showed an illustrative Outcome/Learning preview
  with a filled title). On 2026-10-14 the assertion was reworded to "not even an unfilled sketch" and the
  run regraded as a fail; the re-run is in iteration 7.

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
