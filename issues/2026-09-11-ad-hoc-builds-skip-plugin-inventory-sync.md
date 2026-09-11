## Summary
Ad hoc, plan-driven multi-component plugin builds can skip `plugin-inventory` sync entirely, even
though the mechanism that would catch this already exists and works correctly.

## Environment
- **Product/Service**: `plugin-devkit`'s `plugin-inventory`/`plugin-lifecycle-upstream`, and
  `analysis-kit` as the concrete case that surfaced this
- **Region/Version**: n/a

## Reproduction Steps
1. Build a new component into an existing, already-inventoried plugin (one that already has a minted
   `plugin_id` and an existing `plugin-inventory.json`) via an ad hoc, plan-driven process — e.g. a
   standalone multi-task implementation plan executed directly — rather than through
   `plugin-lifecycle-upstream`'s own gated phases.
2. Commit and push the new component at each "before finalizing" checkpoint along the way, without ever
   invoking `plugin-inventory check`/`plan`/`apply`.
3. Note that nothing in the ad hoc process itself prompts the inventory step — it only exists inside
   `plugin-lifecycle-upstream`'s own "Inventory Sync" step (after Commit, before Document), which never
   runs because the pipeline itself was never invoked.
4. Confirm the gap only surfaces retroactively, if and when something else (e.g. a
   `running-a-full-retrospective` pass) happens to check inventory drift after the fact.

## Expected Behavior
Either the ad hoc build process has its own lightweight reminder to run `plugin-inventory` before each
"before finalizing" checkpoint, or there's some other guard that makes this gap visible sooner than "a
retrospective pass caught it at the very end."

## Actual Behavior
`analysis-kit`'s Wave 2 capability-expansion build added 7 new skills across several build sessions,
each committed and pushed without ever running `plugin-inventory check`/`plan`/`apply` — even though
`analysis-kit` already had a minted `plugin_id` and an existing `plugin-inventory.json` from an earlier
bootstrap (2026-08-29), and even though `plugin-lifecycle-upstream`'s own SKILL.md already has a
dedicated "Inventory Sync" step that would have caught this automatically.

The gap is **not** a missing mechanism — it already exists and works correctly once actually run:
confirmed live this session, `plugin-inventory check` correctly detected all 7 missing components in one
pass, and the plan/apply cycle applied cleanly (retroactively fixed the same session this was found).
The gap is that this Wave 2 build used an ad hoc, plan-driven process (a multi-task implementation plan
executed directly) rather than going through `plugin-lifecycle-upstream`'s own gated phases, so its
Inventory Sync step never had a chance to fire. It was only caught retroactively via a
`running-a-full-retrospective` pass at the very end, after 3 separate "before finalizing" checkpoints had
already shipped without it.

`.claude/rules/require-inventory-updates-for-new-plugins-and-components.md`'s own rule and
`plugin-lifecycle-upstream`'s Inventory Sync step already correctly cover the case — but only for work
that actually goes through that pipeline. An ad hoc multi-session build has no equivalent lightweight
self-check, and `analysis-kit`'s own plugin directory has no `CONTRIBUTING.md` or build-checklist file
where such a reminder could live today.

## Impact
**Low** — no data loss or shipped defect (the gap was caught and fixed retroactively this same session,
before any release), but it's the kind of gap that could persist silently for a long time on a build
that never runs a retrospective pass.

## Additional Context
Proposed fix (not prescriptive — flag for discussion): consider whether an ad hoc/manual multi-component
build process should have its own lightweight reminder (e.g. a build-checklist note, or a
periodic/final `plugin-inventory` check baked into whatever process drives a multi-task plan-based
build), since the formal pipeline's safeguard only helps when the pipeline itself is actually used
end-to-end.

Related (not a duplicate — checked via `gh api search/issues`, none found):
`.claude/rules/require-inventory-updates-for-new-plugins-and-components.md` (the existing rule/mechanism
this gap sits alongside, not a duplicate of); issue #107 ("analysis-kit: consolidated backlog of
remaining minor/informational findings") as a possibly-related tracking issue for analysis-kit process
gaps.
