Before I kick this off, I want to flag some ambiguity rather than guess and burn a lot of time/tokens on the wrong scope — this maps to a few different things depending on what you actually mean.

**What "a full codex audit" could mean here:**
1. Running the `codex-audit-loop` skill (in the available skill list) against this repo — repeated Codex review passes across multiple lenses, looping until no new findings surface.
2. Something closer to `plugin-lifecycle-downstream`'s Audit phase / `plugin-auditor`, which fans out this repo's own reviewer agents (security, structure, naming/rulebook, completeness, etc.) — a different mechanism than Codex specifically.
3. A one-off `cross-model-review` / `code-review --ultra` pass, which is scoped to a diff rather than the whole tree.

These aren't interchangeable, and "the whole project" plus "until convergence" with no other bound is the kind of open-ended, high-effort operation I'd rather not just launch on assumptions, per this repo's own CLAUDE.md ("if multiple interpretations exist, present them — don't pick silently" / "if something is unclear, stop... ask").

**Specific things I'd need pinned down before running this:**

- **Scope of "whole project."** This marketplace repo has many plugins (git-kit, plugin-devkit, codex-kit, analysis-kit, etc.) plus root-level tooling/rules/CLAUDE.md itself. Do you want every plugin audited, or a specific subset? A repo-wide "all lenses, all plugins" pass is a materially different size of job than, say, one plugin.
- **"Many lenses" — which ones, concretely?** E.g. correctness/bugs, security, rule-compliance (R1–R27), structure/completeness, naming, duplication, simplification/efficiency, test coverage. Should this be an unbounded "whatever Codex thinks to check" or a fixed list?
- **"Until convergence" — what's the stop condition?** Options: stop when a round produces zero new findings; stop after N rounds regardless; stop when only advisory/low-severity findings remain. Without a defined criterion this can loop indefinitely or burn an unpredictable amount of budget.
- **Read-only audit, or fix-as-you-go?** An audit that only reports findings is very different from one that also applies fixes back into tracked files — the latter is a shippable change and, per this repo's rules, would need `starting-work` first (never edit on `main` directly) and would trigger the plugin-rulebook / testing / security-review gates for anything touching plugin components.
- **Where should output land?** A consolidated report as a file, or fed straight into a triage/fix workflow?

If you can answer those (or just say "use `codex-audit-loop`, whole repo, standard lens set, stop at zero new findings, report only, no fixes"), I'll proceed on that basis. If you want, I can also propose a sensible default scope myself and just confirm it with you in one shot rather than a long back-and-forth — happy to go either way.
