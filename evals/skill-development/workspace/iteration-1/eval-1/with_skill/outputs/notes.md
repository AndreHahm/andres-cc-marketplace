# Notes: ops-kit / log-triage

Followed skill-development (Greenfield path, plugin-scoped placement).

Assumptions (no way to ask; AskUserQuestion not available):
- Placement: plugin-scoped (`ops-kit/skills/log-triage/`), stated by the user.
- Plugin language declared as Python in `ops-kit/README.md` (repo rule: declare a language); helper is Python.
- Phase 3 (subagent evals / baseline fan-out), Phase 3.5 and description-optimization loop skipped: each needs user approval via AskUserQuestion for cost, and the user asked only for a simple skill. Testing & Validation section documents scenarios instead.
- Official spec fetch not done (no network step taken); relied on bundled references.

Files created (all under outputs/):
- ops-kit/.claude-plugin/plugin.json, ops-kit/README.md
- ops-kit/skills/log-triage/SKILL.md (allowed-tools: Read, Bash(grep:*), Bash(jq:*), Bash(python:*); one Bash entry per command)
- ops-kit/skills/log-triage/scripts/top_errors.py (normalizes + counts recurring error lines)

Verification:
- Ran grep + jq + top_errors.py on a fixture log (scratchpad): found and fixed two script bugs (digit-adjacent numbers like "30s" not masked; JSON lines collapsed because quoted strings were masked). Re-run grouped correctly.
- quick_validate.py passed.
- plugin-rulebook run: caught R29 (missing positive/negative trigger lists) and R28 (no justification); both fixed. R32 data-only boundary included. Other rules (R4-R9, R13, R17, R18, R21, R24, R35) checked by hand: PASS. Rulebook was applied by reading, not by the checker agent.
- Not done: smoke_test.py (user wanted one helper script), executable bit/git mode (nothing committed), mirror/inventory steps (outside outputs dir).
