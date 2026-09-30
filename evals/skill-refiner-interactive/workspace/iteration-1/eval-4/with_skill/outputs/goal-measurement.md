# Goal Measurement (step 8)

Method per references/goal-derivation.md, run after step 7 validation, on OUTDIR/target.

| # | Goal | Source finding | Verification | Result |
|---|---|---|---|---|
| 1 | Zero reference-to-reference chains | ref->ref chain (a.md -> b.md) | Grep `references/*.md` for directives to read another references/ file. Only one file remains, `marker-details.md`, with no such directive. 0 matches. | PASS |
| 2 | All intake uses AskUserQuestion with options | Intake violation ("Ask the user which file to process") | Grep SKILL.md for `ask the user` / `prompt the user`. 0 free-form matches; the Quick Start now has a `questions:` block with `options:`. | PASS |
| 3 | Every invoked tool is declared in allowed-tools | Undeclared tool (Grep used via "grep the file") | Tool-scoping scan. Body invokes `Grep` (and `AskUserQuestion`, which is exempt). `allowed-tools: Read Grep` covers it. No undeclared tools. | PASS |

All 3 selected goals PASS. No FAIL, so the "Accept with reason / Continue refining" ask was not triggered.

Deferred goal candidates (not selected, Minor): missing Goal Verification section; reference cluster (resolved anyway by the step-3 consolidation); missing standard sections (auto-added in step 6).

Simulation note: step 10 (Skill(plugin-rulebook) and skill-reviewer) could not be dispatched in this dry run. It is recorded as not executed, so `<skill-improvement-complete>` is NOT emitted here.
