# Goal measurement (step 8)

Selected goals (all 3 offered, all selected):

| # | Goal | Source finding | Verification | Result |
|---|---|---|---|---|
| 1 | Zero reference->reference chains | ref chain: references/a.md directs "Read references/b.md" | Re-ran chain scan over references/*.md for imperative read/see directives to another references/ file: 0 matches (a.md now only points to SKILL.md's Reference Guide) | PASS |
| 2 | All intake uses AskUserQuestion with options | intake violation: Quick Start "Ask the user which file to process" | Re-ran intake scan (`ask the user`, `prompt the user`, free-form `questions:`): 0 matches; Quick Start now has an AskUserQuestion block with options | PASS |
| 3 | Every invoked tool is declared in allowed-tools | undeclared tool: Grep used in Quick Start, allowed-tools was `Read` | Re-ran tool-scoping scan: allowed-tools is `Read Grep`, no undeclared tools | PASS |

Deferred goal candidates (more than 3 findings): frontmatter single-line description, missing goal verification section, reference cluster (a.md + b.md; consolidation declined at Gate 4).

All goals PASS, so no failed-goal ask was needed.
