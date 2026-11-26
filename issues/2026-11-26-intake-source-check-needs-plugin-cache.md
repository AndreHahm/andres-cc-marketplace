## Summary
`plugin-integration-intake`'s unknown-source check looks for the calling plugin only in the project's `plugins/` tree, so a submission from a plugin installed through the marketplace cache is rejected as an unknown source before any operation runs, `classify` included.

## Environment
- **Product/Service**: `workmanagement-kit`, `plugins/workmanagement-kit/skills/plugin-integration-intake/SKILL.md` step 2 (unknown-source check, lines 75-104 at the commit below)
- **Region/Version**: branch `feat/workmanagement-kit-pr-link-classify-guard` at eee9ca2d4152df773be8110b49146ae2af13105e
- **Browser/OS**: N/A

## Reproduction Steps
Found by review and by reading the skill; not reproduced at runtime.

1. Install `workmanagement-kit` and a calling plugin (for example `workledger-kit`) from the marketplace into an ordinary project, which has no `plugins/` directory.
2. Have the calling plugin submit an intake envelope, for example a `classify` submission.
3. Step 2's check compares `source_plugin` with `plugins/*/.claude-plugin/plugin.json` manifests and resolves `source_skill` under `plugins/<dir>/skills/`. Neither exists in the project.

## Expected Behavior
The existence check finds a calling plugin and skill wherever they are actually installed (the project's `plugins/` tree in this repository, the plugin cache in a standalone install), and still requires exactly one match.

## Actual Behavior
Every submission from a cache-installed plugin ends in the unknown-source structured handoff. PR #913 made the bridge caller find an installed `codex-kit` (issue #279), but a standalone caller never gets past intake's own source check to reach it.

## Error Details
~~~
None (structured handoff: unknown source)
~~~

## Visual Evidence
None.

## Impact
**Medium** - intake, and so `classify`, works only in a source checkout of this repository; no wrong write results.

## Additional Context
- Found in PR #913: https://github.com/AndreHahm/andres-cc-marketplace/pull/913#discussion_r4707133186 (reviewer: Devin, at eee9ca2d's parent f7e1fcf3ba17476e91953d288d706389eb8b9b93).
- The check predates PR #913; `classify` inherits it. Related: #279 (the same standalone-layout assumption, in the bridge caller).
- The allowlist and exactly-one-match rules in step 2 should stay; only where manifests are looked up changes.
