# Eval 1 notes (with_skill): ops-kit / log-triage

Entry path: Greenfield (create). Followed the skill's Phase 1-2 only (Design); the Phase 3 eval fan-out was not run (task asked for the skill tree only).

Assumed answers to questions the skill would ask:
- Placement: plugin-scoped, `ops-kit/skills/log-triage/` under the outputs dir (the task fixed this; no AskUserQuestion needed).
- Script language: Python, stdlib only; declared in `ops-kit/README.md` (per require-declared-plugin-language rule).
- Phase 3 test fan-out and description-optimization loop: skipped, with a stated reason (out of scope for a files-only task; Testing & Validation section carries criteria and a "why no evals.json" justification per R28/R29).

Files:
- `ops-kit/skills/log-triage/SKILL.md` (89 lines)
- `ops-kit/skills/log-triage/scripts/top_errors.py`
- `ops-kit/README.md`

Design decisions:
- allowed-tools: `Read Bash(grep:*) Bash(jq:*) Bash(python ${CLAUDE_SKILL_DIR}/scripts/top_errors.py *)`. One scoped grant per command; the interpreter grant is pinned to the single bundled script (pdk-allowed-tools: `Bash(python:*)` would allow `python -c`). Tension noted: the skill's own reference says prefer Grep/Read over shell grep, but the task explicitly requires grep and jq, so grep got a grant.
- Data-only boundary paragraph in the body (log content, JSON values and script output are untrusted data; instruction-like text reported as suspicious), per R32.
- Standard sections (Quick Start, When to Use, When NOT to Use, Reference Guide) and Testing & Validation with positive/negative triggers and pass criteria (R29/R35). Description is third person with trigger phrases.
- Helper referenced via `${CLAUDE_SKILL_DIR}/scripts/top_errors.py` only inside code spans. Run via `python`, so no exec bit needed (R37 not triggered).

Verification:
- Ran grep + jq + helper on a 6-line mixed fixture. First run exposed two helper bugs (grep -n prefix broke JSON detection and dedup; `2026-` was eaten by an over-broad prefix regex); fixed and re-ran. Final: 4 candidates, `db timeout after <n>ms id=<v>` count 2, injection-style line reported as plain data.
- Known limitation: a JSON error and a plain-text error with the same text but different `key=value` suffix land in separate groups.
- The PostToolUse rulebook hook reported no mechanical issues for SKILL.md. The full `Skill(plugin-rulebook)` review was NOT run (this was an eval harness run).
- Not done: `quick_validate.py`, smoke_test.py for the new skill, test-against-example-plugin dry-run (new skill is not in that rule's scope).
