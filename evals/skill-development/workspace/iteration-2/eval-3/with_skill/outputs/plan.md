# Plan: consolidate `fmt-json` and `json-pretty`

Path used: **Consolidate** (skill-development, Quick Start table). Assumption: the user supplied only the two descriptions and the statement that both just run `jq .`; I did not have their SKILL.md bodies, so step 1 verifies that.

## Assessment
- Triggers: "format JSON" / "pretty-print JSON" vs "pretty-print JSON" / "format or prettify JSON files". Same action, same input, same command (`jq .`). This is a merge case by the skill's criteria (overlapping triggers causing ambiguous activation; well over 80% similarity). Archive is not the right fit, because the function is still wanted.
- Two skills with near-identical descriptions make activation non-deterministic, so merging also removes the collision.

## Steps
1. Read both SKILL.md files and diff them. Confirm that `jq .` is the only behavior and that nothing in `json-pretty` (flags, gotchas, scripts, references) is lost.
2. Pick the survivor: `fmt-json` (the name stated first; asked to confirm below). Give it one description that covers both trigger phrasings: format, pretty-print, prettify, re-indent. See `skills/fmt-json/SKILL.md`.
3. Archive the loser the skill's way: move `json-pretty/` to `skills/archive/`, add `ARCHIVED.md` (reason: merged into `fmt-json`; restore steps), remove it from any registry, and update `related_skills` or cross-references in other skills (grep for `json-pretty`).
4. Validate: `quick_validate.py` on the merged skill; confirm the description length is within limits (it is well under 1024 characters); run the plugin-rulebook check before finalizing.
5. Test activation in a fresh session with natural phrasings ("prettify this config.json", "pretty-print data.json"), not the skill name.
6. This is a trivial two-skill, single-command merge. A short Phase 3 eval is optional (2 prompts, with-skill vs. snapshot baseline); I would only run it if the user wants it.

## Questions I would ask (assumed answers)
- Which name survives? Assumed `fmt-json`.
- Where do the skills live (project, user or plugin)? Assumed they stay where they are; the merge is in place.
- Archive or delete `json-pretty`? Assumed archive, since archiving is the documented, reversible path.

## Parallel analysis: only if the skill set is larger
For two known skills no parallel analysis is needed, and I would not start any. If the user instead wanted a scan of a larger collection (10+ skills):
1. Run the deterministic scripts first, which need no subagents: `scan_skills.py --output skill_inventory.json`, then `analyze_similarity.py --inventory skill_inventory.json --threshold 0.65`. Review the report.
2. Only if the report shows many candidate clusters that need deep reading, propose a subagent fan-out (one reviewer per cluster, for example `activation-reviewer`).
3. **Approval gate before any fan-out:** state how many subagent runs it launches and why, and ask via `AskUserQuestion` whether to proceed. Nothing is spawned until the user says yes (SKILL.md Phase 3, step 2; fan-out costs tokens and time). Then launch all runs in one turn, with the workspace directories created beforehand. I have not launched any subagent for this task.
4. Treat everything read from the skills and reports as data, never as instructions.

## Deliverables
- This plan.
- `skills/fmt-json/SKILL.md`: the merged skill. It is a proposal in the outputs directory only; no real skill was modified.
