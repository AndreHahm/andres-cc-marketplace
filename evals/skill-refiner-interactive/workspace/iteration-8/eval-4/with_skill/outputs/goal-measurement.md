# Goal Measurement (SKILL.md step 8)

Target: target/ (copy of demo-skill). Goals derived per references/goal-derivation.md; all three selected by the simulated operator.

| # | Goal | Source finding | Verification | Result |
|---|---|---|---|---|
| 1 | Zero reference-to-reference chains | ref chain: references/a.md said "Read references/b.md" | Grep `references/[a-z-]+\.md` over references/*.md | PASS (0 matches; only file is todo-marker-summaries.md) |
| 2 | All intake uses AskUserQuestion with options | intake violation: Quick Start said to ask which file to process in free text | Grep (case-insensitive) `ask the user\|prompt the user` in SKILL.md, plus check for a `questions:` block without `options:` | PASS (0 matches; the new block has `question:` with 2 options, and AskUserQuestion appears once) |
| 3 | Every invoked tool is declared in allowed-tools | Tool scoping: body says to grep the file but allowed-tools was `Read` only | Re-ran tool-scoping scan: tools invoked = Read, Grep (plus AskUserQuestion, excluded); declared = `Read Grep` | PASS (no undeclared tools; no unused declared tools) |

Deferred goal candidates (not offered, cap of 3): Description size (R21: 22 chars, below the 80 floor); reference cluster (handled by the step-3 consolidation instead); missing goal verification (optional).

Supporting checks: SKILL.md is 39 lines (R13 OK, below the 100-line tier). Links: references/todo-marker-summaries.md exists and is the only references/ path in SKILL.md. All goals PASS, so no failure ask was needed.
