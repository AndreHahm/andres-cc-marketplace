## Summary
Generated Codex agent exports drop the source agent's `tools` limit, and the generated boundary note does not say which tools the agent may use, so a read-only reviewer has no instruction against editing files.

## Environment
- **Product/Service**: `scripts/marketplace_ci/conversion.py` (`convert_agent()`, `_CODEX_BOUNDARY_NOTE`), generated `.codex/agents/*.toml`
- **Region/Version**: `main` as of 2026-11-13
- **Browser/OS**: n/a

## Reproduction Steps
1. Read `plugins/plugin-devkit/agents/command-reviewer.md`: its frontmatter sets `tools: ["Read", "Grep", "Glob"]`.
2. Read the generated `.codex/agents/command-reviewer.toml`: there is no `tools` key (Codex's agent schema has none), and the body has no instruction against editing files or running state-changing commands.
3. Repeat for `permission-reviewer`, `hook-reviewer`, `rule-reviewer` and `subagent-reviewer`.

## Expected Behavior
An exported agent whose source is limited to read-only tools tells the Codex agent that limit in its instructions, since Codex cannot enforce it (issue #700: a custom agent runs with the parent session's tools and sandbox).

## Actual Behavior
`convert_agent()` drops `tools` (correctly, since Codex has no such field) but does not carry the list anywhere. The generated boundary note says to "treat the tool and edit restrictions stated below as instructions", but for agents whose body states no such restriction there is nothing below to follow. Under a `workspace-write` parent session, such a reviewer can edit the files it reviews.

## Error Details
~~~
None. The gap is silent.
~~~

## Visual Evidence
n/a

## Impact
**Medium** - A Codex reviewer meant to be read-only has no instruction against editing, so content under review could steer it into changing files. The parent session's sandbox is the only real limit, and this repo's `.codex/config.toml` sets `workspace-write`.

## Additional Context
- Found by the cross-model review of the PR for branch `fix/register-codex-agent-exports` (Codex Phase 1, confirmed by Claude's Phase 2 pass). That PR did not introduce the gap: the hand-maintained exports it replaced had the same inheritance and no boundary note at all.
- Proposed fix: have `convert_agent()` add the source's tool list to the generated note, for example "Your source agent may use only Read, Grep and Glob: do not edit files or run commands that change state." That fixes every export at once instead of editing each agent body.
- `conversion.py` is Tier-1, so the fix needs the maintainer bypass attestation. Update `tests/marketplace_ci/test_conversion.py` and `docs/codex-subagents-schema.md` ("No sandbox in the exports") with it.
- Related: #700, #568, #713.
