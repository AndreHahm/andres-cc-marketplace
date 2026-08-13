# Worked Handoff Example

A filled-out Phase 12 update, following `build-handoff-writer`'s own Output Format
template exactly (see `agents/build-handoff-writer.md`), showing every field this
pipeline's own run record can populate on a **second** dispatch — i.e. the report
already existed from a `plugin-lifecycle-upstream` build, and this pipeline's Phase 12
folded a full twelve-phase run into it. This is illustrative only: field values are
invented for a fictitious `widget-kit` plugin, not drawn from a real run.

**R18 exception (recorded):** the block below is ~46 lines, above the rulebook's
30-line Critical threshold — it's a single coherent worked example whose pedagogical
value depends on showing every section of a real report at once, mirroring the same
exception `build-handoff-writer.md`'s own Output Format template already records for
the identical reason.

```
# Build Handoff: widget-kit

**Generated:** 2026-08-10T14:02:00Z
**Last updated:** 2026-08-13T18:47:00Z
**Pipeline artifacts:** .claude/output/plugin-ideation/widget-kit-concept.md, .claude/output/plugin-planning/widget-kit-plan.md

## What Was Built
A three-skill plugin (`widget-inspect`, `widget-generate`, `widget-validate`) for
scaffolding and validating internal "widget" component manifests.

## How to Use It
`Skill(widget-inspect)` on an existing manifest; `Skill(widget-generate)` for a new one;
`widget-validate` runs automatically as part of both.

## Commits
| SHA | Message | Files |
|---|---|---|
| a1b2c3d | feat(widget-kit): scaffold three core skills | 9 files |
| e4f5a6b | fix(widget-kit): close 2 Major findings from Phase 6 (Fix & Re-audit) | 2 files |
| c7d8e9f | docs(widget-kit): update README per Phase 9 | 1 file |

## Open Items
- `dependency-reviewer:M2` (Major, dependency cycle risk between `widget-generate` and
  `widget-validate`) — recorded `deferred` at Phase 6's attempt limit; rationale: fixing
  requires a shared-schema extraction out of scope for this run, tracked separately.
- Phase 7 (Deep Test) was run **Scoped**, not Full — only the 2 components Phase 6 just
  touched got exhaustive trigger-phrase coverage; the third component's Deep Test
  coverage remains from an earlier run.
- Phase 11 (Grading) declined by the user — no score attached to this update.

## Downstream QA
**Score:** not run (Phase 11 declined — see Open Items)
**Gates applied:** N/A (no grading run)
**Weakest component:** N/A (no grading run)
**Final verification (Phase 10):** current and passing — every check affected by Phases
2, 4, 6, 8, and 9 was re-run against live files; no regression found; 1 finding
(`dependency-reviewer:M2` above) remains `deferred`, correctly excluded from "current and
passing" rather than silently counted as resolved.
**Scope manifest:** `.claude/output/plugin-lifecycle-downstream/run-2026-08-13-004/scope.json`, revision 2 (full-plugin scope, not scoped/named)

## Source Artifacts
- `.claude/output/plugin-lifecycle-downstream/run-2026-08-13-004/scope.json` (rev 2)
- `.claude/output/plugin-lifecycle-downstream/run-2026-08-13-004/validate-report.yaml` (rev 1)
- `.claude/output/plugin-lifecycle-downstream/run-2026-08-13-004/audit-report.yaml` (rev 2, post-Phase-6 re-audit)
- `.claude/output/plugin-lifecycle-downstream/run-2026-08-13-004/deep-test-report.yaml` (rev 1, Scoped)
- `.claude/output/plugin-lifecycle-downstream/run-2026-08-13-004/final-verification-bundle.yaml` (rev 1)
```

**What this example demonstrates:**

- The **Downstream QA** section's shape when Grading was declined — every sub-field
  still gets an explicit value (`not_run`/`N/A`), never omitted, per `SKILL.md`'s Quality
  Gates ("Phase 12 discloses stopped, skipped, deferred, and accepted-risk items").
- A `deferred` finding surfaces in **both** Open Items and as a caveat inside the Final
  Verification line — the same finding, described from two different angles (what's
  still open; why Final Verification's "passing" claim doesn't silently absorb it).
- **Source Artifacts** lists every report *revision* actually referenced, not just the
  latest one per report type — `audit-report.yaml (rev 2, post-Phase-6 re-audit)` makes
  explicit that Phase 6 produced a new revision rather than overwriting the original
  (`SKILL.md`'s "Never overwrite an original report" rule).
- **Scoped Deep Test coverage inherited from an earlier run** is stated plainly in Open
  Items rather than implied by Deep Test's absence from this run's own dispatch list —
  a reader should never have to infer "were the other components ever Deep-Tested" from
  silence.
