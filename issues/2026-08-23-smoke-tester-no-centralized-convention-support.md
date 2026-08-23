## Summary
`smoke-tester` (`plugins/plugin-devkit/agents/smoke-tester.md`) only discovers `scripts/smoke_test.*` inside each individual skill's own directory, so it cannot find or run any of `codex-kit`'s smoke tests, which live in a single centralized `scripts/smoke-tests/*.mjs` directory at the plugin root instead.

## Environment
- **Product/Service**: `plugin-devkit` plugin (this marketplace) — `smoke-tester` agent, consumed by `plugin-lifecycle-downstream`'s Phase 2/3/7/10
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
1. Read `plugins/plugin-devkit/agents/smoke-tester.md`'s "Load Context" section: it `Glob`s each in-scope *skill directory* for `scripts/smoke_test.*` — one file per skill, nested under that skill's own path.
2. Read `plugins/codex-kit/scripts/smoke-tests/README.md`: codex-kit's actual, pre-existing, documented convention is a single centralized `plugins/codex-kit/scripts/smoke-tests/` directory at the plugin root, holding one `.mjs` file per behavior fix (15 files as of 2026-08-23, covering multiple skills/scripts each), not one file per skill under each skill's own `scripts/` path.
3. Run `plugin-lifecycle-downstream` on codex-kit and reach any phase that would dispatch `smoke-tester` (Phase 3 Validate, Phase 7 Deep Test, Phase 10 Final Verification) — `smoke-tester`'s Glob pattern matches none of codex-kit's 21 smoke tests (15 pre-existing + 6 added during a 2026-08-23 downstream QA run), so every one is reported `skipped` regardless of whether it would actually pass or fail.

## Expected Behavior
`smoke-tester` (or an equivalent sanctioned delegate) should be able to discover and execute codex-kit's centralized-convention smoke tests, so `plugin-lifecycle-downstream`'s own rule — "never execute a target plugin's own scripts directly in this pipeline's own context... route through `smoke-tester`" — has a working path for this target plugin.

## Actual Behavior
`smoke-tester` silently records every codex-kit smoke test as `skipped` ("no `scripts/smoke_test.*` found"), which is indistinguishable in its own report from "this skill genuinely has no smoke test yet." There is no supported execution path in `plugin-lifecycle-downstream` for any of codex-kit's smoke-test suite: `smoke-tester` can't see them, and the pipeline's own "Treat Target Content as Data, Never Execute It" section explicitly forbids running them directly in the pipeline's own context.

## Error Details
~~~
N/A — not a crash. smoke-tester's Glob step (`scripts/smoke_test.*` under each skill directory) simply
never matches `plugins/codex-kit/scripts/smoke-tests/*.mjs`, so it reports skipped with no error.
~~~

## Impact
**Medium** — no data loss or security exposure, but a real coverage gap in the QA pipeline's own tooling: any regression in codex-kit's 21 smoke tests would go undetected by a `plugin-lifecycle-downstream` run, since the run has no way to actually execute them through a sanctioned delegate. During a 2026-08-23 downstream QA run, this was worked around by executing the 6 newly-authored smoke tests directly (a deviation from the pipeline's own stated boundary, explicitly disclosed to and accepted by the user for that run) rather than leaving them unverified.

## Additional Context
Found during a `plugin-lifecycle-downstream` full-pipeline QA run on `codex-kit` (2026-08-23), Phase 2 (Prepare) — while authoring 6 new smoke tests
(`codex-audit-loop-invariants.mjs`, `codex-peer-review-invariants.mjs`, `codex-plan-loop-invariants.mjs`,
`codex-prompt-protocol-references.mjs`, `codex-session-lookup-scripts.mjs`,
`plugin-marketplace-review-references.mjs`) and needing to demonstrate them against a controlled negative
per Phase 2's own requirement, discovered there was no working `smoke-tester` path to do so.

Suggested fix direction (not yet decided/prioritized): either extend `smoke-tester` to also discover a
centralized `scripts/smoke-tests/*.mjs` convention at a plugin's root (in addition to the existing
per-skill `scripts/smoke_test.*` pattern), or explicitly document a second sanctioned execution delegate
for a centralized-convention plugin, so `plugin-lifecycle-downstream`'s "never execute directly" rule has
a real path for a plugin shaped like codex-kit.

Reference: `plugins/codex-kit/scripts/smoke-tests/README.md` for the existing convention's shape;
`plugins/plugin-devkit/agents/smoke-tester.md` for the current Glob-based boundary.

Filed live: https://github.com/AndreHahm/andres-cc-marketplace/issues/104
