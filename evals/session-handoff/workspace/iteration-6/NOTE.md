# Iteration 6 (2026-11-20): template v2 (PR B)

CREATE Step 2 item 5 became a state table (`state` and `context_mode` in the frontmatter, with the new
`ready-to-publish` state), and RESUME Step 3 reads the frontmatter and the Resume Card first. Evals 4-5 and 7-13
were reworded for the frontmatter, eval 6 now covers an older handoff's 'Context mode:' line, evals 14-16 cover the
card-first load, and eval 17 covers `ready-to-publish`. Each eval ran plan-only, with-skill only, in a fresh
subagent that read the worktree's SKILL.md by path (a Skill() dispatch would have loaded main's unedited copy).
No baseline arm. Result: 20/20 assertions across evals 4-17.
