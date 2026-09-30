# Goal Measurement: demo-skill

| Goal | Source finding | Verification | Result |
|---|---|---|---|
| G1: Zero reference->reference chains | `references/a.md` directed a read of `references/b.md` | Re-ran the chain scan over `references/*.md` | PASS (0 matches; a.md and b.md merged into `references/todo-markers.md`) |
| G2: Every invoked tool is declared in `allowed-tools` | Body says "grep the file" but only `Read` was declared | Re-ran the tool-scoping scan | PASS (invoked Read, Grep; declared `Read Grep`; none undeclared) |
| G3: `description` within R21 tiers | `description` was 22 characters (floor 80) | R21 check (mechanical length measurement; `Skill(plugin-rulebook)` itself was simulated) | PASS (~165 characters, within 80-1024; no when_to_use; combined within 80-1536) |

No goal failed, so "Accept with reason" was never needed. Deferred goal candidates (not selected): reference cluster (resolved anyway by the step-3 consolidation), missing goal verification section (optional).
