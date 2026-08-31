# Test Scenarios

Full 29-scenario test walkthrough for `plugin-grader`, extracted from `SKILL.md`'s own
`## Testing & Validation` section per `plugin-rulebook`'s R30 (content beyond R29's required
trigger-example lists and pass-criteria checklist must move to `references/` or `evals.json`, not stay
inline in `SKILL.md`).

**Last dated run record:** `.claude/output/plugin-grader/example-plugin-2026-08-31T16-02-07Z.md` — the
two new script invocations Step 8 relies on (`plugin-inventory.py import-grading` and
`marketplace-inventory.py import-grading`) were live-dry-run against a scratch copy of `example-plugin`'s
real `plugin-inventory.json` and the repo's real `marketplace-inventory.json`: a synthetic component-mode
report imported cleanly (`quality_score_appended`/`security_score_appended` both `true`), a same-report
re-import correctly reported both as `false` (scenario 14d's no-op case), and a synthetic plugin-mode
report imported cleanly into the marketplace-level rollup. `scripts/smoke_test.py` re-run and passing
after the SKILL.md edit (frontmatter/Bash-grant consistency, including the two new grants). Scenarios
14-14h below are design-review-verified against this real run and two rounds of `cross-model-review`
(which found and fixed the plugin-mode partial-existence gap, the under-disclosed consent question, and
the plugin-mode partial-completion disclosure gap). Scenarios 14i-14k were added after PR #271's own
Codex and Devin review rounds found that Step 8 offered (and, in evidence-only mode, could actually
attempt) an import that either couldn't succeed (a refusal has no score to import) or violated
`plugin-lifecycle-downstream` Phase 11's own no-plugin-mutation contract, plus a hardcoded
`plugins/<name>/` path assumption that breaks for a target resolved outside this marketplace's own
layout — fixed by excluding evidence-only mode from Step 8 entirely and resolving the plugin directory
from Step 1's own resolution instead of a reconstructed string. See `evals/plugin-grader/evals.json`
for scenarios 14, 14a-14k as structured eval entries (added in the same PR round) — not yet run through
a full `skill-tester` baseline-vs-with_skill comparison pass.

1. **Single skill, clean** — grade a skill with no findings from any dispatched reviewer; confirm all 12 dimensions score 10 and `final_score` is 10.0 with no gates
2. **Rule compliance gate** — grade a target with a known REQUIRED rule violation; confirm Gate A fires and `final_score` is capped at 6.0
2a. **Safety gate** — grade a target with a Critical `safety_risk_handling` finding (e.g. `Bash(*)`); confirm Gate C fires and `final_score` is capped at 4.0, even when every other dimension scores 10
2b. **Testing gate** — grade a target with `testing == 0.0` (no `evals/`, no Testing & Validation section of its own); confirm Gate D fires, `final_score` is capped at 8.0, and the output includes the literal comment `"Missing verification."` exactly as `gates-and-rollup.md` specifies
3. **Gate stacking** — construct an input triggering both Gate A and Gate B; confirm `final_score` uses the *lower* of the two caps (5.0), not the first one found. Also confirm stacking Gate B and Gate C uses 4.0 (the lower of the two), since Gate C is now the lowest cap of the four
4. **N/A dimension** — grade a component with no `scripts/`; confirm `robustness` scores 10 with `is_na: true`, not excluded from the weighted sum
5. **Plugin rollup with one broken component** — construct component scores where one is < 3; confirm Gate P3 fires and `weakest_component` is reported even though the mean looks acceptable
6. **Fast mode** — confirm the Fast-mode flag reaches `plugin-auditor`, `scripts-reviewer`/`consistency-reviewer`/`security-reviewer` are skipped, and `notes.inspection_limits` states this
7. **Self-check** — `scripts/smoke_test.py` passes (this skill's own persisted smoke test), re-run after any SKILL.md edit
8. **Evidence-only mode, missing evidence → refusal** (new, M3) — invoke evidence-only mode with a scope manifest naming a component that has no corresponding report in the supplied evidence bundle; confirm scoring is refused (not silently skipped or scored as if clean) per `references/output-schema.md`'s refusal shape, and confirm no `plugin-auditor`/reviewer/test dispatch was attempted
8a. **Evidence-only mode, stale evidence → qualified score** — supply evidence whose `current_commit` doesn't match the scope manifest's; confirm the score is returned qualified, with `notes.inspection_limits` stating the staleness, not refused outright and not silently ignored
8b. **Evidence-only mode, complete and fresh → identical scoring** — supply a complete, fresh evidence bundle for a target already graded via standalone mode in scenario 1; confirm the two runs produce the same `final_score`/`gates_applied` (the dispatch mechanism differs, the scoring doesn't)
9. **Plugin security rollup, clean** — every component scores `safety_risk_handling: 10`; confirm `plugin_security_score` is `10.0` with no gate
10. **Gate P4 fires** — one component scores `safety_risk_handling: 2.0`; confirm `plugin_security_score` is capped at `4.0` even though the mean of all components would be higher, and confirm `plugin_final_score` is unaffected (Gate P4 never caps it)
11. **All components N/A** — every component's `safety_risk_handling` is `is_na: true`; confirm `plugin_security_score` is `10.0` (matching the existing N/A-defaults-to-10 rule), not `null`
12. **No security-scorable components** — a plugin whose components all have a `final_score` (quality is gradeable) but none has a `safety_risk_handling` dimension to report (e.g. every component is a type this skill can't assess for security); `component_scores` is still populated, only `component_security_scores` is omitted. Confirm `plugin_security_score` is `null` with a stated reason in `notes.security_score_unavailable_reason`, not a fabricated value. (A plugin with zero gradeable components at all is a different, harder failure — `compute_score.py --rollup` raises on an empty `component_scores`, since there is nothing to roll up; that case is reported as a refusal, not a `null` score.)
13. **Schema-version field presence** — confirm a freshly-generated report (either mode) always carries `grader_schema_version: "1.1.0"`, and that a pre-existing report with no `grader_schema_version` key at all is distinguishable by that field's absence alone
14. **Offer Inventory Import, no inventory exists** — grade a target whose plugin has no `plugin-inventory.json` yet (and, in plugin mode, no `marketplace-inventory.json`); confirm the offer is skipped outright (no `AskUserQuestion` fired) and the gap is stated plainly in the narrative summary instead
14a. **Offer Inventory Import, component mode, accepted** — grade a single component whose plugin already has a `plugin-inventory.json`; accept the offer; confirm exactly one `plugin-inventory import-grading` call runs against the just-written report path, and both `quality_score_appended`/`security_score_appended` are reported back to the user
14b. **Offer Inventory Import, declined** — decline the offer at either mode; confirm no `Bash` call to either inventory script is made
14c. **Offer Inventory Import, plugin mode, accepted** — grade a whole plugin with 3 components, all already tracked in that plugin's `plugin-inventory.json`; accept the offer; confirm 3 per-component `plugin-inventory import-grading` calls run (each against a freshly extracted single-component report file, never the combined plugin-mode report), plus exactly one `marketplace-inventory import-grading` call for the plugin rollup
14d. **Offer Inventory Import, re-importing the same report is a no-op** — accept the offer in scenario 14a, then trigger the import a second time against the *same, already-written report file* (not a fresh grading run — a fresh grade always stamps a new `graded_at` and therefore a different `report_sha256`, which would append as a new event, not dedupe); confirm the second import's `quality_score_appended`/`security_score_appended` are both reported as `false` (a legitimate no-op — same report hash already imported) rather than presented as if new history landed
14e. **Offer Inventory Import, import-grading rejects the report** — construct a target/type mismatch between the grading target and the inventory record it's imported against; confirm the script's `SystemExit` error is surfaced to the user verbatim, and no partial write occurs
14f. **Offer Inventory Import, plugin mode, partial existence** — grade a whole plugin whose own `plugin-inventory.json` exists but the repo has no `marketplace-inventory.json` yet (or vice versa); confirm the question discloses which half will run before asking, and confirm only the sub-step whose target file exists is attempted — never an unconditional attempt against the missing one, and never a script failure with no prior disclosure
14g. **Offer Inventory Import, plugin-mode question discloses scope** — grade a whole plugin with 3 components, both target files present; confirm the `AskUserQuestion` text itself states the component count and mentions the plugin rollup, not the bare component-mode phrasing reused verbatim
14h. **Offer Inventory Import, plugin mode, partial-completion failure** — construct a plugin-mode grade where one component's `(name, type)` has no matching record in `plugin-inventory.json` (a stale inventory) while the others do; confirm the components before the failing one are reported as successfully imported, the failing one's error is surfaced separately, and the rollup step's own run/skip status is stated — never a single collapsed pass/fail line that hides which components actually got written
14i. **Offer Inventory Import, evidence-only mode never runs** — invoke evidence-only mode (as `plugin-lifecycle-downstream`'s Phase 11 would) and produce a normal scored report; confirm Step 8 is skipped entirely — no existence check, no `AskUserQuestion`, no write, no narrative note about missing inventory — since Phase 11's own contract forbids modifying the plugin during that phase
14j. **Offer Inventory Import, evidence-only refusal never reaches Step 8** — invoke evidence-only mode with missing/stale required evidence, producing a refusal-shaped report (no `final_score`/`graded_at`); confirm Step 8 is skipped for the same reason as 14i (mode exclusion), not because of a separate "is this report scored" check — there is no such check, since evidence-only mode never reaches this step at all
14k. **Offer Inventory Import, target resolved outside the marketplace layout** — grade a component/plugin whose target resolves to a directory not under this repo's own `plugins/<name>/` (a path-resolved target per Step 1's own Usage section); confirm the existence check Globs the *actual resolved* plugin directory's `.claude-plugin/plugin-inventory.json`, not a `plugins/<name>/`-shaped string reconstructed from the target's bare name — a real inventory file at the resolved location must be found, not silently reported as missing
